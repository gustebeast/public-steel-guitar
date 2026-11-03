/* The CH32V307 boards' USB loader, at the bottom of flash (output_panel, motor_ctrl; each
 * builds this file against its own link.c and link.h). Written once with the WCH-LinkE; every
 * later firmware goes in over USB (usbflash.py on the Pi).
 *
 * Every power-up it enumerates and waits WINDOW_US for a host to say H. Then it resets and
 * starts the application from a clean chip, if the record says the application is whole
 * (length and CRC-32, written last). The watchdog starts before the application does, and the
 * application has to keep feeding it: one that hangs is reset back here, and comes up again in
 * this window, until usbflash.py catches one. An application asks for the loader with
 * reset_to(GO_LOADER).
 *
 * The line protocol, one reply line per command:
 *   H                    stay in the loader                   -> OK
 *   I                    -> BOOT 1 <app ok 0/1> <len hex> <crc hex>
 *   E <len>              drop the record, erase the application's sectors -> OK
 *   W <addr> <crc>       then PAGE raw bytes, to flash at addr -> OK
 *   C <len> <crc>        check the flash, write the record    -> OK
 *   G                    start the application                -> OK
 * addr is a flash offset; nothing under APP_ORG can be written, the record excepted. */
#include <stdlib.h>
#include <string.h>
#include "UART.h"
#include "link.h"

#define WINDOW_US 1500000u
#define REC_MAGIC 0x50534731u
#define WATCHDOG_S 8u                     /* the application's start-up has to fit inside it */
struct rec { uint32_t magic, len, crc, not_crc; };
#define REC ((const struct rec *)(FLASH_BASE_ADDR + REC_ORG))

void NMI_Handler(void) __attribute__((interrupt));
void HardFault_Handler(void) __attribute__((interrupt));
void NMI_Handler(void) { }
void HardFault_Handler(void) { NVIC_SystemReset(); while (1) { } }

static uint32_t crc32(const uint8_t *p, uint32_t n)
{
    uint32_t c = ~0u;
    while (n--) {
        c ^= *p++;
        for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320u & -(c & 1));
    }
    return ~c;
}

static int app_ok(void)
{
    const struct rec *r = REC;
    return r->magic == REC_MAGIC && r->crc == ~r->not_crc && r->len && r->len <= FLASH_END - APP_ORG
           && crc32((const uint8_t *)(FLASH_BASE_ADDR + APP_ORG), r->len) == r->crc;
}

static char *hex(char *p, uint32_t v)
{
    for (int i = 7; i >= 0; i--) *p++ = "0123456789abcdef"[(v >> (4 * i)) & 15];
    return p;
}

static uint32_t page[PAGE / 4];
static uint32_t page_at, page_crc, page_got;
static int hold;

static void info(void)
{
    char l[40], *p = l;
    memcpy(p, "BOOT 1 ", 7); p += 7;
    *p++ = app_ok() ? '1' : '0'; *p++ = ' ';
    p = hex(p, REC->len); *p++ = ' ';
    p = hex(p, REC->crc); *p++ = '\n';
    link_send(l, (uint16_t)(p - l));
}

static int erase(uint32_t at, uint32_t n)
{
    return FLASH_ROM_ERASE(FLASH_BASE_ADDR + at, n) == FLASH_COMPLETE;
}

static void line(char *s)
{
    uint32_t a, b;
    char c = s[0], *e = s + 1;
    a = strtoul(e, &e, 16); b = strtoul(e, &e, 16);
    switch (c) {
    case 'H': hold = 1; link_say("OK\n"); break;
    case 'I': info(); break;
    case 'E': {
        hold = 1;
        uint32_t n = (a + SECTOR - 1) & ~(SECTOR - 1);
        if (!a || n > FLASH_END - APP_ORG) { link_say("ERR len\n"); break; }
        link_say(erase(REC_ORG, SECTOR) && erase(APP_ORG, n) ? "OK\n" : "ERR erase\n");
        break;
    }
    case 'W':
        if (a < APP_ORG || a + PAGE > FLASH_END || a % PAGE) { link_say("ERR addr\n"); break; }
        page_at = a; page_crc = b; page_got = 1;     /* the bytes come next */
        break;
    case 'C': {
        struct rec r = { REC_MAGIC, a, b, ~b };
        static uint32_t buf[PAGE / 4];
        if (!a || a > FLASH_END - APP_ORG
            || crc32((const uint8_t *)(FLASH_BASE_ADDR + APP_ORG), a) != b) {
            link_say("ERR crc\n"); break;
        }
        memset(buf, 0xFF, sizeof buf); memcpy(buf, &r, sizeof r);
        link_say(FLASH_ROM_WRITE(FLASH_BASE_ADDR + REC_ORG, buf, PAGE) == FLASH_COMPLETE && app_ok()
                 ? "OK\n" : "ERR record\n");
        break;
    }
    case 'G':
        if (!app_ok()) { link_say("ERR no app\n"); break; }
        link_say("OK\n");
        Delay_Ms(20);
        reset_to(GO_APP);
        break;
    default: link_say("ERR ?\n");
    }
}

static void byte_in(uint8_t c)
{
    static char ln[48]; static uint8_t n;
    if (page_got) {
        ((uint8_t *)page)[page_got - 1] = c;
        if (++page_got <= PAGE) return;
        page_got = 0;
        if (crc32((uint8_t *)page, PAGE) != page_crc) { link_say("ERR crc\n"); return; }
        link_say(FLASH_ROM_WRITE(FLASH_BASE_ADDR + page_at, page, PAGE) == FLASH_COMPLETE
                 && !memcmp((void *)(FLASH_BASE_ADDR + page_at), page, PAGE) ? "OK\n" : "ERR write\n");
        return;
    }
    if (c == '\r') return;
    if (c == '\n') { ln[n] = 0; if (n) line(ln); n = 0; }
    else if (n < sizeof ln - 1) ln[n++] = (char)c;
}

static void watchdog_start(void)
{
    IWDG_WriteAccessCmd(IWDG_WriteAccess_Enable);
    IWDG_SetPrescaler(IWDG_Prescaler_256);     /* LSI 40 kHz: 156 Hz */
    IWDG_SetReload(WATCHDOG_S * 156);
    IWDG_ReloadCounter();
    IWDG_Enable();                        /* only a reset stops it */
}

int main(void)
{
    uint32_t go = BOOT_WORDS[0], chk = BOOT_WORDS[1];
    BOOT_WORDS[0] = 0; BOOT_WORDS[1] = 0;
    if (go == GO_APP && chk == ~GO_APP) {
        watchdog_start();
        __disable_irq();
        ((void (*)(void))APP_ORG)();
    }
    if (go == GO_LOADER && chk == ~GO_LOADER) hold = 1;
    if (!app_ok()) hold = 1;
    link_init();
    uint64_t end = now_us() + WINDOW_US;
    static uint8_t pkt[LINK_PACKET];
    while (1) {
        int got = link_take(pkt);
        for (int i = 0; i < got; i++) byte_in(pkt[i]);
        if (!hold && now_us() > end) reset_to(GO_APP);
    }
}
