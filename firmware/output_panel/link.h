#ifndef LINK_H
#define LINK_H
#include <stdint.h>
#include "ch32v30x.h"
#include "ch32v30x_usbhs_device.h"

/* Flash, at the chip's 0x08000000 alias: [loader 28 K][record 4 K][application].
 * The application is linked at APP_ORG (0x8000 in the link map). */
#define FLASH_BASE_ADDR 0x08000000u
#define APP_ORG    0x8000u
#define REC_ORG    0x7000u
#define FLASH_END  (288u * 1024u)
#define PAGE       256u
#define SECTOR     4096u
#define LINK_PACKET DEF_USB_HS_PACK_LEN

/* Two words the linker scripts leave out of RAM, so they survive a reset: what the next boot does. */
#define BOOT_WORDS ((volatile uint32_t *)0x20007FF0u)
#define GO_LOADER  0x4C4F4144u      /* stay in the loader */
#define GO_APP     0x41505021u      /* start the checked application, no window */

void link_init(void);
int link_up(void);
void link_send(const void *d, uint16_t n);
void link_say(const char *s);
int link_take(uint8_t *dst);        /* one packet from the host, or -1 */
uint64_t now_us(void);
void Delay_Us(uint32_t n);
void Delay_Ms(uint32_t n);
void reset_to(uint32_t what);
#endif
