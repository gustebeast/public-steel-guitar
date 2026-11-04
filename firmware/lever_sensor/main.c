/* lever_sensor application: the MA730's angle at SAMPLE_US, filtered and calibrated (lever.c),
 * out on bus B as CAN frames (the ids are in lever.h).
 *
 * Board (elec/lever_sensor.py): CH32V203G6U6 (32 K flash, 10 K RAM), 8 MHz crystal, run at
 * 48 MHz. CAN1 on PA11 (RX) / PA12 (TX), the only pins this package gives it. Two rules from WCH's
 * datasheet table 3-1-3: PB8 is BOOT0's pin, tied to GND, so it is never an output; PA10 is the
 * same pin as PA11, so it is never an output either.
 *
 * No interrupts: one loop reads the sensor, takes frames from the controller's FIFO and gives
 * it frames, and feeds the watchdog. Calibration and slot live in the last 256-byte page of
 * flash (CFG_AT). */
#include "ch32v20x.h"
#include "lever.h"
#include "ma730.h"

#define CFG_AT  (FLASH_BASE + 32u * 1024u - 256u)
#define UID_AT  0x1FFFF7E8u                 /* 96-bit unique id (WCH RM, electronic signature) */
#define CAN_BPS 500000u                     /* motor_ctrl's bus B default */
#ifndef HAVE_LOADER
#define HAVE_LOADER 0
#endif

static uint32_t ticks_per_us;

static uint64_t now_us64(void)
{
    volatile uint32_t *p = (volatile uint32_t *)&SysTick->CNT;
    uint32_t hi, lo;
    do { hi = p[1]; lo = p[0]; } while (hi != p[1]);
    return (((uint64_t)hi << 32) | lo) / ticks_per_us;
}

static uint32_t now_us(void) { return (uint32_t)now_us64(); }

void Delay_Us(uint32_t n)
{
    uint64_t end = now_us64() + n;
    while (now_us64() < end) { }
}

void Delay_Ms(uint32_t n) { Delay_Us(n * 1000u); }

static void clock_init(void)
{
    SystemCoreClockUpdate();
    ticks_per_us = SystemCoreClock / 1000000u;
    SysTick->CTLR = 0; SysTick->CNT = 0; SysTick->CMP = ~0ULL;
    SysTick->CTLR = 0x5;                    /* count HCLK, upward, no reload */
}

static void watchdog_init(void)
{   /* LSI 40 kHz / 32 = 1.25 kHz, 500 counts: 400 ms, over a 20 ms MA730 register write */
    IWDG_WriteAccessCmd(IWDG_WriteAccess_Enable);
    IWDG_SetPrescaler(IWDG_Prescaler_32);
    IWDG_SetReload(500);
    IWDG_ReloadCounter();
    IWDG_Enable();
}

static void can_filter(uint8_t slot)
{   /* 16-bit list mode: this board's CMD id and the broadcast, nothing else */
    uint16_t all = (uint16_t)(ID_ALL << 5);
    CAN_FilterInitTypeDef f = {0};
    f.CAN_FilterNumber = 0;
    f.CAN_FilterMode = CAN_FilterMode_IdList;
    f.CAN_FilterScale = CAN_FilterScale_16bit;
    f.CAN_FilterIdHigh = slot < SLOTS ? (uint16_t)((ID_CMD + slot) << 5) : all;
    f.CAN_FilterIdLow = all;
    f.CAN_FilterMaskIdHigh = all;
    f.CAN_FilterMaskIdLow = all;
    f.CAN_FilterFIFOAssignment = CAN_Filter_FIFO0;
    f.CAN_FilterActivation = ENABLE;
    CAN_FilterInit(&f);
}

static void can_init(uint8_t slot)
{
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_AFIO, ENABLE);
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_CAN1, ENABLE);
    GPIO_InitTypeDef g = {0};
    g.GPIO_Speed = GPIO_Speed_50MHz;
    g.GPIO_Pin = GPIO_Pin_12; g.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_Init(GPIOA, &g);
    g.GPIO_Pin = GPIO_Pin_11; g.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_Init(GPIOA, &g);

    RCC_ClocksTypeDef ck;
    RCC_GetClocksFreq(&ck);
    CAN_InitTypeDef c = {0};
    c.CAN_Prescaler = (uint16_t)(ck.PCLK1_Frequency / (16u * CAN_BPS));   /* 16 quanta, as motor_ctrl */
    c.CAN_Mode = CAN_Mode_Normal;
    c.CAN_SJW = CAN_SJW_1tq; c.CAN_BS1 = CAN_BS1_13tq; c.CAN_BS2 = CAN_BS2_2tq;
    c.CAN_ABOM = ENABLE;                    /* back from bus-off by itself */
    c.CAN_NART = DISABLE;                   /* retry until acknowledged */
    c.CAN_TXFP = ENABLE;                    /* in the order given */
    CAN_Init(CAN1, &c);
    can_filter(slot);
}

static int mailbox_free(void)
{
    return (CAN1->TSTATR & (CAN_TSTATR_TME0 | CAN_TSTATR_TME1 | CAN_TSTATR_TME2)) != 0;
}

static void can_send(const lever_frame_t *f)
{
    CanTxMsg m = {0};
    if (f->ext) { m.ExtId = f->id; m.IDE = CAN_Id_Extended; }
    else { m.StdId = f->id; m.IDE = CAN_Id_Standard; }
    m.RTR = CAN_RTR_Data;
    m.DLC = f->len;
    for (int i = 0; i < f->len; i++) m.Data[i] = f->d[i];
    CAN_Transmit(CAN1, &m);
}

static int can_take(lever_frame_t *f)
{
    if (!CAN_MessagePending(CAN1, CAN_FIFO0)) return 0;
    CanRxMsg m;
    CAN_Receive(CAN1, CAN_FIFO0, &m);
    if (m.RTR != CAN_RTR_Data) return 0;
    f->ext = m.IDE == CAN_Id_Extended;
    f->id = f->ext ? m.ExtId : m.StdId;
    f->len = m.DLC > 8 ? 8 : m.DLC;
    for (int i = 0; i < f->len; i++) f->d[i] = m.Data[i];
    return 1;
}

static int cfg_save(const lever_cfg_t *c)
{
    static uint32_t page[64];
    for (int i = 0; i < 64; i++) page[i] = 0xFFFFFFFFu;
    const uint32_t *w = (const uint32_t *)c;
    for (uint32_t i = 0; i < sizeof *c / 4; i++) page[i] = w[i];
    IWDG_ReloadCounter();
    if (FLASH_ROM_ERASE(CFG_AT, 256) != FLASH_COMPLETE) return 0;
    if (FLASH_ROM_WRITE(CFG_AT, page, 256) != FLASH_COMPLETE) return 0;
    const uint32_t *f = (const uint32_t *)CFG_AT;
    for (int i = 0; i < 64; i++) if (f[i] != page[i]) return 0;
    return 1;
}

static uint32_t board_uid(void)
{
    uint32_t u[3];
    for (int i = 0; i < 3; i++) u[i] = ((const volatile uint32_t *)UID_AT)[i];
    return lever_crc32(u, sizeof u);
}

int main(void)
{
    static lever_t l;
    lever_frame_t f;

    clock_init();
    watchdog_init();
    ma730_init();
    lever_init(&l, (const lever_cfg_t *)CFG_AT, board_uid(), now_us());
    if (l.cfg.mglt != 0xFF) ma730_thresholds(l.cfg.mglt, l.cfg.mght);
    can_init(l.cfg.slot);

    uint32_t t_sample = now_us(), t_field = t_sample;
    uint8_t slot = l.cfg.slot;
    for (;;) {
        IWDG_ReloadCounter();
        uint32_t now = now_us();
        if (now - t_sample >= SAMPLE_US) {
            t_sample += SAMPLE_US;
            if (now - t_sample >= SAMPLE_US) t_sample = now;    /* fell behind (a flash write) */
            lever_sample(&l, ma730_angle());
        }
        if (now - t_field >= FIELD_US) {
            t_field = now;
            lever_field(&l, ma730_field());
        }
        while (can_take(&f)) lever_rx(&l, &f);
        if (l.want_loader) {
            l.want_loader = 0;
            if (!HAVE_LOADER) l.reply.d[1] = 0;            /* no loader on this board yet */
        }
        if (l.want_thresh) {
            l.want_thresh = 0;
            ma730_thresholds(l.cfg.mglt, l.cfg.mght);
        }
        if (l.want_save) {
            l.want_save = 0;
            if (cfg_save(&l.cfg)) l.unsaved = 0;
            else if (l.reply_n) l.reply.d[1] = 0;
        }
        if (l.cfg.slot != slot) { slot = l.cfg.slot; can_filter(slot); }
        while (mailbox_free() && lever_poll(&l, now_us(), &f)) can_send(&f);
    }
}
