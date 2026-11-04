#ifndef LDR_H
#define LDR_H
/* The lever board's CAN loader protocol, with no hardware in it (boot.c moves its frames and
 * owns the flash; the Pi's simulator runs this same file against a pretend flash).
 *
 * FLASH MAP (32 K):  0x0000 loader (boot.c, LDR_MAX)    0x2800 application (main.c, APP_MAX)
 *                    0x7E00 the loader's RECORD of the application    0x7F00 config (lever.h)
 * The loader starts the application only if the record says how long it is and its CRC matches,
 * so an update that stops halfway leaves the board in the loader, on the bus, not bricked. The
 * loader is written once, by SWD, and never over CAN.
 *
 * BUS B, 11-bit, by slot (a board with no slot is given one first, with the broadcast 'S',
 * which the loader answers as the application does):
 *   0x400+slot  LDR    Pi -> loader  op u8, then:
 *                        'I'                    -> 'I' ok, loader version, app ok
 *                        'E' len u32            erase the record and len of application
 *                        'W' page u16, crc u32  the next 32 DATA frames are that page
 *                        'C' len u24, crc u32   the whole image's CRC; if it matches, the record
 *                        'G'                    -> 'G' ok, then restart (into the application)
 *   0x480+slot  LDR_R  loader -> Pi  op u8, ok u8, then the op's own bytes ('W': page u16)
 *   0x500+slot  DATA   Pi -> loader  8 bytes of the current page, in order
 * Every frame is at most 8 bytes, op included. CRCs are lever_crc32 (zlib's). The application goes to the loader on CMD 'B' (lever.h). */
#include "lever.h"

#define ID_LDR      0x400u
#define ID_LDR_R    0x480u
#define ID_LDR_D    0x500u
#define LDR_VERSION 1
#define LDR_MAX     0x2800u
#define APP_AT      0x2800u
#define REC_AT      0x7E00u
#define CFG_AT_OFF  0x7F00u
#define APP_MAX     (REC_AT - APP_AT)
#define LDR_PAGE    256u
#define REC_MAGIC   0x41505031u                 /* "APP1" */
#define BOOT_STAY   0x4C445231u                 /* the application asks the loader to stay */
#define LDR_WINDOW_US 1000000u                  /* after a watchdog reset: a chance to catch it */

typedef struct {
    int (*erase)(uint32_t off, uint32_t n);     /* 256-aligned, offsets from the flash base; 1 ok */
    int (*write)(uint32_t off, const uint32_t *page);    /* one LDR_PAGE */
    const uint8_t *flash;                       /* the whole 32 K, as it reads */
    uint8_t slot;
    uint8_t paging, got;                        /* in a page; DATA frames so far */
    uint16_t page_no;
    uint32_t page_crc;
    uint32_t page[LDR_PAGE / 4];
    uint8_t reply_n, go, heard;                 /* heard: any LDR frame since start */
    lever_frame_t reply;
} ldr_t;

void ldr_init(ldr_t *b, const uint8_t *flash, int (*erase)(uint32_t, uint32_t),
              int (*write)(uint32_t, const uint32_t *), uint8_t slot);
int ldr_app_ok(const uint8_t *flash);          /* the record and the image agree */
void ldr_rx(ldr_t *b, const lever_frame_t *in);
int ldr_poll(ldr_t *b, lever_frame_t *out);
#endif
