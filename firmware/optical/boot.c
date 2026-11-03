/* The optical board's USB loader, at the bottom of flash. Written once with the ST-LINK; every
 * later firmware goes in over USB (../output_panel/usbflash.py on the Pi). output_panel's
 * boot.c with the same line protocol, on this chip's flash and TinyUSB.
 *
 * Every power-up it enumerates and waits WINDOW_MS for a host to say H. Then it resets and
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
#include "board.h"
#include "tusb.h"

#define WINDOW_MS 2000u
#define REC_MAGIC 0x50534731u
#define WATCHDOG_S 8u                     /* the application's start-up has to fit inside it */
struct rec { uint32_t magic, len, crc, not_crc; };
#define REC ((const struct rec *)(FLASH_BASE + REC_ORG))

void HardFault_Handler(void) { NVIC_SystemReset(); }

static uint32_t crc32(const uint8_t *p, uint32_t n)
{
    uint32_t c = ~0u;
    while (n--) {
        c ^= *p++;
        for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320u & -(c & 1));
    }
    return ~c;
}

static void watchdog_start(void)
{
    IWDG1->KR = 0xCCCC;                   /* on, from LSI at 32 kHz; only a reset stops it */
    IWDG1->KR = 0x5555;
    IWDG1->PR = 6;                        /* /256: 125 Hz */
    IWDG1->RLR = WATCHDOG_S * 125;
    while (IWDG1->SR) { }
    IWDG1->KR = 0xAAAA;
}

static int app_ok(void)
{
    const struct rec *r = REC;
    return r->magic == REC_MAGIC && r->crc == ~r->not_crc && r->len && r->len <= FLASH_LEN - APP_ORG
           && crc32((const uint8_t *)(FLASH_BASE + APP_ORG), r->len) == r->crc;
}

static void say(const char *s)
{
    tud_cdc_n_write_str(0, s);
    tud_cdc_n_write_flush(0);
}

static char *hex(char *p, uint32_t v)
{
    for (int i = 7; i >= 0; i--) *p++ = "0123456789abcdef"[(v >> (4 * i)) & 15];
    return p;
}

static void info(void)
{
    char l[40], *p = l;
    memcpy(p, "BOOT 1 ", 7); p += 7;
    *p++ = app_ok() ? '1' : '0'; *p++ = ' ';
    p = hex(p, REC->len); *p++ = ' ';
    p = hex(p, REC->crc); *p++ = '\n'; *p = 0;
    say(l);
}

/* flash words are 32 bytes, written whole, from a word-aligned source */
static uint32_t page[PAGE / 4] __attribute__((aligned(32)));
static uint32_t page_at, page_crc, page_got;
static int hold;

static int erase(uint32_t at, uint32_t n)
{
    FLASH_EraseInitTypeDef e = {0};
    uint32_t bad = 0;
    e.TypeErase = FLASH_TYPEERASE_SECTORS;
    e.Banks = FLASH_BANK_1;
    e.Sector = at / SECTOR;
    e.NbSectors = n / SECTOR;
    e.VoltageRange = FLASH_VOLTAGE_RANGE_3;
    HAL_FLASH_Unlock();
    int ok = HAL_FLASHEx_Erase(&e, &bad) == HAL_OK;
    HAL_FLASH_Lock();
    return ok;
}

static int program(uint32_t at, const uint32_t *src, uint32_t n)
{
    int ok = 1;
    HAL_FLASH_Unlock();
    for (uint32_t i = 0; ok && i < n; i += 32)
        ok = HAL_FLASH_Program(FLASH_TYPEPROGRAM_FLASHWORD, FLASH_BASE + at + i,
                               (uint32_t)src + i) == HAL_OK;
    HAL_FLASH_Lock();
    return ok;
}

static void line(char *s)
{
    uint32_t a, b;
    char c = s[0], *e = s + 1;
    a = strtoul(e, &e, 16); b = strtoul(e, &e, 16);
    switch (c) {
    case 'H': hold = 1; say("OK\n"); break;
    case 'I': info(); break;
    case 'E': {
        hold = 1;
        uint32_t n = (a + SECTOR - 1) & ~(SECTOR - 1);
        if (!a || n > FLASH_LEN - APP_ORG) { say("ERR len\n"); break; }
        say(erase(REC_ORG, SECTOR) && erase(APP_ORG, n) ? "OK\n" : "ERR erase\n");
        break;
    }
    case 'W':
        if (a < APP_ORG || a + PAGE > FLASH_LEN || a % PAGE) { say("ERR addr\n"); break; }
        page_at = a; page_crc = b; page_got = 1;     /* the bytes come next */
        break;
    case 'C': {
        struct rec r = { REC_MAGIC, a, b, ~b };
        static uint32_t buf[8] __attribute__((aligned(32)));
        if (!a || a > FLASH_LEN - APP_ORG
            || crc32((const uint8_t *)(FLASH_BASE + APP_ORG), a) != b) {
            say("ERR crc\n"); break;
        }
        memset(buf, 0xFF, sizeof buf); memcpy(buf, &r, sizeof r);
        say(program(REC_ORG, buf, sizeof buf) && app_ok() ? "OK\n" : "ERR record\n");
        break;
    }
    case 'G':
        if (!app_ok()) { say("ERR no app\n"); break; }
        say("OK\n");
        for (uint32_t t = HAL_GetTick(); HAL_GetTick() - t < 20; ) tud_task();
        reset_to(GO_APP);
        break;
    default: say("ERR ?\n");
    }
}

static void byte_in(uint8_t c)
{
    static char ln[48]; static uint8_t n;
    if (page_got) {
        ((uint8_t *)page)[page_got - 1] = c;
        if (++page_got <= PAGE) return;
        page_got = 0;
        if (crc32((uint8_t *)page, PAGE) != page_crc) { say("ERR crc\n"); return; }
        say(program(page_at, page, PAGE)
            && !memcmp((void *)(FLASH_BASE + page_at), page, PAGE) ? "OK\n" : "ERR write\n");
        return;
    }
    if (c == '\r') return;
    if (c == '\n') { ln[n] = 0; if (n) line(ln); n = 0; }
    else if (n < sizeof ln - 1) ln[n++] = (char)c;
}

int main(void)
{
    uint32_t go = BOOT_WORDS[0], chk = BOOT_WORDS[1];
    BOOT_WORDS[0] = 0; BOOT_WORDS[1] = 0;
    if (go == GO_APP && chk == ~GO_APP) {
        const uint32_t *v = (const uint32_t *)(FLASH_BASE + APP_ORG);
        watchdog_start();
        __disable_irq();
        SCB->VTOR = FLASH_BASE + APP_ORG;
        __set_MSP(v[0]);
        __enable_irq();
        ((void (*)(void))v[1])();
    }
    if (go == GO_LOADER && chk == ~GO_LOADER) hold = 1;
    HAL_Init();
    clock_setup();
    if (!app_ok()) hold = 1;
    usb_pins();
    usb_setup();
    uint32_t t0 = HAL_GetTick();
    while (1) {
        tud_task();
        while (tud_cdc_n_available(0)) byte_in((uint8_t)tud_cdc_n_read_char(0));
        if (!hold && HAL_GetTick() - t0 > WINDOW_MS) reset_to(GO_APP);
    }
}
