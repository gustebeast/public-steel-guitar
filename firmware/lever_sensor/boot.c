/* lever_sensor CAN loader, at 0x0000 (ldr.h has the flash map and the protocol). Written once,
 * by SWD; everything after it -- every application -- goes in over bus B.
 *
 * At reset it starts the application at once, unless
 *   - the application asked it to stay (CMD 'B': BOOT_STAY in BOOT_WORDS), or
 *   - the record and the image do not agree (never written, or an update stopped halfway), or
 *   - the watchdog reset the board: then it listens LDR_WINDOW_US first, so an application that
 *     hangs over and over can still be caught and replaced, and goes on if nobody asks.
 * While it waits it is a lever board with no sensor: it answers the broadcast and its slot's
 * CMD as the application does (HELLO says mode 1), so a board is found and given a slot here too.
 *
 * It stays in machine mode (the Makefile patches WCH's startup), because the application's
 * startup, which it jumps to, writes machine CSRs. */
#include "hw.h"
#include "ldr.h"

static void filter_ids(uint8_t slot, uint16_t ids[4])
{
    if (slot < SLOTS) {
        ids[0] = (uint16_t)(ID_CMD + slot); ids[1] = (uint16_t)ID_ALL;
        ids[2] = (uint16_t)(ID_LDR + slot); ids[3] = (uint16_t)(ID_LDR_D + slot);
    } else {
        ids[0] = ids[1] = ids[2] = ids[3] = (uint16_t)ID_ALL;
    }
}

static void start_app(void)
{
    ((void (*)(void))(uintptr_t)APP_AT)();
    while (1) { }
}

int main(void)
{
    static lever_t l;
    static ldr_t b;
    lever_frame_t f;
    uint16_t ids[4];
    const uint8_t *flash = (const uint8_t *)FLASH_BASE;

    int stay = BOOT_WORDS[0] == BOOT_STAY && BOOT_WORDS[1] == ~BOOT_STAY;
    BOOT_WORDS[0] = 0; BOOT_WORDS[1] = 0;
    int dog = (RCC->RSTSCKR & RCC_IWDGRSTF) != 0;
    RCC->RSTSCKR |= RCC_RMVF;
    int app = ldr_app_ok(flash);
    if (app && !stay && !dog) start_app();

    clock_init();
    lever_init(&l, (const lever_cfg_t *)(FLASH_BASE + CFG_AT_OFF), hw_uid(), now_us());
    l.mode = 1;
    ldr_init(&b, flash, hw_erase, hw_write, l.cfg.slot);
    uint8_t slot = l.cfg.slot;
    hw_bus_init();
    filter_ids(slot, ids);
    hw_can_init(ids);

    uint32_t t0 = now_us(), t_start = t0;
    for (;;) {
        IWDG_ReloadCounter();                       /* running only if the application started it */
        while (hw_can_take(&f)) { lever_rx(&l, &f); ldr_rx(&b, &f); }
        if (l.want_save) {
            l.want_save = 0;
            if (hw_cfg_save(&l.cfg)) l.unsaved = 0;
            else if (l.reply_n) l.reply.d[1] = 0;
        }
        l.want_loader = l.want_thresh = 0;          /* here already; no sensor to set */
        if (l.want_release) hw_release(l.want_release, l.release_cycle);
        if (l.want_next) { hw_next(l.want_next == 1); l.want_next = 0; }
        else if (!l.held && now_us() - t_start >= NEXT_AFTER_US) { hw_next(1); l.held = 1; }
        if (l.cfg.slot != slot) {
            slot = b.slot = l.cfg.slot;
            filter_ids(slot, ids); hw_can_filter(ids);
        }
        while (hw_mailbox_free() && (ldr_poll(&b, &f) || lever_poll(&l, now_us(), &f))) hw_can_send(&f);
        if (b.go && hw_tx_idle()) NVIC_SystemReset();
        if (dog && app && !stay && !b.heard && now_us() - t0 >= LDR_WINDOW_US) start_app();
    }
}
