/* What the optical board's loader and application share: the clock tree, the PHY's pins, the
 * USB core, and how one asks a reset to land in the other. */
#ifndef BOARD_H_
#define BOARD_H_
#include "stm32h7xx_hal.h"

/* Flash, bank 1, in 128 K sectors: the loader, its record of the application, the application */
#define SECTOR    0x20000u
#define REC_ORG   0x20000u
#define APP_ORG   0x40000u
#define FLASH_LEN 0x100000u
#define PAGE      4096u

/* The word a reset carries from one image to the other. DTCM survives a reset, and neither
 * linker script puts anything in it. */
#define BOOT_WORDS ((volatile uint32_t *)0x2001FFF8)
#define GO_APP     0x41505031u
#define GO_LOADER  0x424F4F54u

int clock_setup(void);
void pin(GPIO_TypeDef *port, uint32_t pins, uint32_t mode, uint32_t speed, uint32_t af);
void usb_pins(void);
int usb_setup(void);
void reset_to(uint32_t go);

#endif
