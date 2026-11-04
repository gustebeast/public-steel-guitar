#ifndef LINK_H
#define LINK_H
#include <stdint.h>
#include "ch32v30x.h"
#include "ch32v30x_usbfs_device.h"

#ifndef REV
#define REV 1
#endif
/* R2 (make REV=2): J4 is a CH340C on USART1, PA9 TX / PA10 RX, and every byte goes in a frame
 * (frame.h). THE link's one speed, for both ends: bench/publicbench/frames.py reads it from
 * here. A CH343P in U7's place is this line and nothing else (6 Mbaud: 96 MHz / 16). */
#define LINK_BAUD  2000000u

/* Flash, at the chip's 0x08000000 alias: [loader 28 K][record 4 K][application].
 * The application is linked at APP_ORG (0x8000 in the link map). */
#define FLASH_BASE_ADDR 0x08000000u
#define APP_ORG    0x8000u
#define REC_ORG    0x7000u
#define FLASH_END  (288u * 1024u)
#define PAGE       256u
#define SECTOR     4096u
#if REV == 1
#define LINK_PACKET DEF_USB_FS_PACK_LEN
#else
#include "frame.h"
#define LINK_PACKET FRAME_MAX       /* one frame's payload */
#endif

/* Two words the linker scripts leave out of RAM, so they survive a reset: what the next boot does. */
#define BOOT_WORDS ((volatile uint32_t *)0x20007FF0u)
#define GO_LOADER  0x4C4F4144u      /* stay in the loader */
#define GO_APP     0x41505021u      /* start the checked application, no window */

void link_init(void);
int link_up(void);
void link_send(const void *d, uint16_t n);
void link_say(const char *s);
int link_take(uint8_t *dst);        /* one packet (R2: one frame) from the host, or -1 */
uint64_t now_us(void);
void Delay_Us(uint32_t n);
void Delay_Ms(uint32_t n);
void reset_to(uint32_t what);
#if REV != 1
uint32_t link_bad(void);            /* frames dropped on the way in: CRC, COBS or length */
int link_tx_busy(void);             /* a frame is still going out */
#endif
#endif
