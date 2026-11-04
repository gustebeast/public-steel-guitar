/* The lever board's hardware: see hw.h. */
#include "hw.h"
#include "ldr.h"

static uint32_t ticks_per_us;

static uint64_t now_us64(void)
{
    volatile uint32_t *p = (volatile uint32_t *)&SysTick->CNT;
    uint32_t hi, lo;
    do { hi = p[1]; lo = p[0]; } while (hi != p[1]);
    return (((uint64_t)hi << 32) | lo) / ticks_per_us;
}

uint32_t now_us(void) { return (uint32_t)now_us64(); }

void Delay_Us(uint32_t n)
{
    uint64_t end = now_us64() + n;
    while (now_us64() < end) { }
}

void Delay_Ms(uint32_t n) { Delay_Us(n * 1000u); }

void clock_init(void)
{
    SystemCoreClockUpdate();
    ticks_per_us = SystemCoreClock / 1000000u;
    SysTick->CTLR = 0; SysTick->CNT = 0; SysTick->CMP = ~0ULL;
    SysTick->CTLR = 0x5;                    /* count HCLK, upward, no reload */
}

/* The pair and the power switches (elec/lever_sensor.py). Each one's resistor holds the safe
 * state while the pin floats -- in reset, and in WCH's ROM loader:
 *   PB3 USB_SEL    high: the pair goes to the terminator (CAN); pulled low: to PB6 / PB7 (USB)
 *   PB4 XCVR_EN_N  low: the transceiver is powered; pulled high: off, its bus pins high-Z
 *   PB5 DS_EN      high: the next board has 5 V; pulled low: it is dark */
#define PIN_SEL  GPIO_Pin_3
#define PIN_XCVR GPIO_Pin_4
#define PIN_DS   GPIO_Pin_5

void hw_bus_init(void)
{
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);
    GPIO_SetBits(GPIOB, PIN_SEL | PIN_XCVR);         /* levels first, then drive them */
    GPIO_ResetBits(GPIOB, PIN_DS);
    GPIO_InitTypeDef g = {0};
    g.GPIO_Speed = GPIO_Speed_2MHz; g.GPIO_Mode = GPIO_Mode_Out_PP;
    g.GPIO_Pin = PIN_SEL | PIN_XCVR | PIN_DS;
    GPIO_Init(GPIOB, &g);
    GPIO_ResetBits(GPIOB, PIN_XCVR);                 /* transceiver on */
    Delay_Us(100);
    GPIO_SetBits(GPIOB, PIN_DS);                     /* then the next board */
}

void hw_release(uint16_t ms)
{
    GPIO_InitTypeDef g = {0};
    g.GPIO_Speed = GPIO_Speed_2MHz; g.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    g.GPIO_Pin = GPIO_Pin_8 | GPIO_Pin_9;            /* CAN pins off the dead transceiver */
    GPIO_Init(GPIOB, &g);
    GPIO_SetBits(GPIOB, PIN_XCVR);                   /* transceiver off; PB3 stays high */
    GPIO_ResetBits(GPIOB, PIN_DS);                   /* next board dark ... */
    uint32_t t = now_us();
    while (now_us() - t < (uint32_t)ms * 1000u) IWDG_ReloadCounter();
    GPIO_SetBits(GPIOB, PIN_DS);                     /* ... and back, onto a USB pair */
    for (;;) IWDG_ReloadCounter();                   /* until the arm is power-cycled */
}

void hw_can_filter(const uint16_t ids[4])
{   /* 16-bit list mode: these four standard ids, nothing else */
    CAN_FilterInitTypeDef f = {0};
    f.CAN_FilterNumber = 0;
    f.CAN_FilterMode = CAN_FilterMode_IdList;
    f.CAN_FilterScale = CAN_FilterScale_16bit;
    f.CAN_FilterIdHigh = (uint16_t)(ids[0] << 5);
    f.CAN_FilterIdLow = (uint16_t)(ids[1] << 5);
    f.CAN_FilterMaskIdHigh = (uint16_t)(ids[2] << 5);
    f.CAN_FilterMaskIdLow = (uint16_t)(ids[3] << 5);
    f.CAN_FilterFIFOAssignment = CAN_Filter_FIFO0;
    f.CAN_FilterActivation = ENABLE;
    CAN_FilterInit(&f);
}

void hw_can_init(const uint16_t ids[4])
{
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB | RCC_APB2Periph_AFIO, ENABLE);
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_CAN1, ENABLE);
    GPIO_PinRemapConfig(GPIO_Remap1_CAN1, ENABLE);   /* RX PB8, TX PB9 */
    GPIO_InitTypeDef g = {0};
    g.GPIO_Speed = GPIO_Speed_2MHz;                 /* slow edges: 500 kbit/s needs no more */
    g.GPIO_Pin = GPIO_Pin_9; g.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_Init(GPIOB, &g);
    g.GPIO_Pin = GPIO_Pin_8; g.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_Init(GPIOB, &g);

    RCC_ClocksTypeDef ck;
    RCC_GetClocksFreq(&ck);
    CAN_InitTypeDef c = {0};
    c.CAN_Prescaler = (uint16_t)(ck.PCLK1_Frequency / (16u * CAN_BPS));   /* 16 quanta, as motor_ctrl */
    c.CAN_Mode = CAN_Mode_Normal;
    c.CAN_SJW = CAN_SJW_1tq; c.CAN_BS1 = CAN_BS1_13tq; c.CAN_BS2 = CAN_BS2_2tq;
    c.CAN_ABOM = ENABLE;                    /* back from bus-off by itself */
    c.CAN_NART = DISABLE;                   /* retry until acknowledged */
    c.CAN_TXFP = ENABLE;                    /* in the order given */
    CAN_DeInit(CAN1);
    CAN_Init(CAN1, &c);
    hw_can_filter(ids);
}

int hw_mailbox_free(void)
{
    return (CAN1->TSTATR & (CAN_TSTATR_TME0 | CAN_TSTATR_TME1 | CAN_TSTATR_TME2)) != 0;
}

int hw_tx_idle(void)
{
    uint32_t all = CAN_TSTATR_TME0 | CAN_TSTATR_TME1 | CAN_TSTATR_TME2;
    return (CAN1->TSTATR & all) == all;
}

void hw_can_send(const lever_frame_t *f)
{
    CanTxMsg m = {0};
    if (f->ext) { m.ExtId = f->id; m.IDE = CAN_Id_Extended; }
    else { m.StdId = f->id; m.IDE = CAN_Id_Standard; }
    m.RTR = CAN_RTR_Data;
    m.DLC = f->len;
    for (int i = 0; i < f->len; i++) m.Data[i] = f->d[i];
    CAN_Transmit(CAN1, &m);
}

int hw_can_take(lever_frame_t *f)
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

int hw_erase(uint32_t off, uint32_t n)
{
    IWDG_ReloadCounter();
    int ok = FLASH_ROM_ERASE(FLASH_BASE + off, n) == FLASH_COMPLETE;
    IWDG_ReloadCounter();
    return ok;
}

int hw_write(uint32_t off, const uint32_t *page)
{
    IWDG_ReloadCounter();
    return FLASH_ROM_WRITE(FLASH_BASE + off, (uint32_t *)page, LDR_PAGE) == FLASH_COMPLETE;
}

int hw_cfg_save(const lever_cfg_t *c)
{
    static uint32_t page[LDR_PAGE / 4];
    for (uint32_t i = 0; i < LDR_PAGE / 4; i++) page[i] = 0xFFFFFFFFu;
    const uint32_t *w = (const uint32_t *)c;
    for (uint32_t i = 0; i < sizeof *c / 4; i++) page[i] = w[i];
    if (!hw_erase(CFG_AT_OFF, LDR_PAGE) || !hw_write(CFG_AT_OFF, page)) return 0;
    const uint32_t *f = (const uint32_t *)(FLASH_BASE + CFG_AT_OFF);
    for (uint32_t i = 0; i < LDR_PAGE / 4; i++) if (f[i] != page[i]) return 0;
    return 1;
}

uint32_t hw_uid(void)
{
    uint32_t u[3];
    for (int i = 0; i < 3; i++) u[i] = ((const volatile uint32_t *)UID_AT)[i];
    return lever_crc32(u, sizeof u);
}
