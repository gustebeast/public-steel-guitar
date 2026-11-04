/* lever_sensor application: the MA730's angle at SAMPLE_US, filtered and calibrated (lever.c),
 * out on bus B as CAN frames (the ids are in lever.h). It runs at APP_AT, under the CAN loader
 * (boot.c, ldr.h), which is how it is updated: CMD 'B' sends the board there.
 *
 * Board (elec/lever_sensor.py): CH32V203G6U6 (32 K flash, 10 K RAM), 8 MHz crystal, run at
 * 48 MHz. CAN1 on PA11 (RX) / PA12 (TX), the only pins this package gives it. Two rules from WCH's
 * datasheet table 3-1-3: PB8 is BOOT0's pin, tied to GND, so it is never an output; PA10 is the
 * same pin as PA11, so it is never an output either.
 *
 * No interrupts: one loop reads the sensor, takes frames from the controller's FIFO and gives
 * it frames, and feeds the watchdog. Calibration and slot live in the last 256-byte page of
 * flash (CFG_AT_OFF), shared with the loader. */
#include "hw.h"
#include "ldr.h"
#include "ma730.h"

static void watchdog_init(void)
{   /* LSI 40 kHz / 32 = 1.25 kHz, 500 counts: 400 ms, over a 20 ms MA730 register write */
    IWDG_WriteAccessCmd(IWDG_WriteAccess_Enable);
    IWDG_SetPrescaler(IWDG_Prescaler_32);
    IWDG_SetReload(500);
    IWDG_ReloadCounter();
    IWDG_Enable();
}

static void filter_ids(uint8_t slot, uint16_t ids[4])
{
    ids[0] = slot < SLOTS ? (uint16_t)(ID_CMD + slot) : (uint16_t)ID_ALL;
    ids[1] = ids[2] = ids[3] = (uint16_t)ID_ALL;
}

static void to_loader(lever_t *l)
{   /* the reply ("ok") goes out first, then the restart */
    lever_frame_t f;
    uint32_t t = now_us();
    while (now_us() - t < 50000u) {
        IWDG_ReloadCounter();
        if (hw_mailbox_free() && lever_poll(l, now_us(), &f)) hw_can_send(&f);
        else if (hw_tx_idle()) break;
    }
    BOOT_WORDS[0] = BOOT_STAY; BOOT_WORDS[1] = ~BOOT_STAY;
    NVIC_SystemReset();
    while (1) { }
}

int main(void)
{
    static lever_t l;
    lever_frame_t f;
    uint16_t ids[4];

    clock_init();
    watchdog_init();
    ma730_init();
    lever_init(&l, (const lever_cfg_t *)(FLASH_BASE + CFG_AT_OFF), hw_uid(), now_us());
    if (l.cfg.mglt != 0xFF) ma730_thresholds(l.cfg.mglt, l.cfg.mght);
    filter_ids(l.cfg.slot, ids);
    hw_can_init(ids);

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
        while (hw_can_take(&f)) lever_rx(&l, &f);
        if (l.want_thresh) {
            l.want_thresh = 0;
            ma730_thresholds(l.cfg.mglt, l.cfg.mght);
        }
        if (l.want_save) {
            l.want_save = 0;
            if (hw_cfg_save(&l.cfg)) l.unsaved = 0;
            else if (l.reply_n) l.reply.d[1] = 0;
        }
        if (l.want_loader) to_loader(&l);
        if (l.cfg.slot != slot) { slot = l.cfg.slot; filter_ids(slot, ids); hw_can_filter(ids); }
        while (hw_mailbox_free() && lever_poll(&l, now_us(), &f)) hw_can_send(&f);
    }
}
