#ifndef HW_H
#define HW_H
/* The lever board's hardware, shared by the application (main.c) and the loader (boot.c):
 * the clock, the bus pair and the next board's power, CAN1 on PB8 / PB9 (remap 1), the flash,
 * the unique id. Board facts in main.c's header. */
#include "ch32v20x.h"
#include "lever.h"

#define CAN_BPS    500000u                  /* motor_ctrl's bus B default */
#define UID_AT     0x1FFFF7E8u              /* 96-bit unique id (WCH RM, electronic signature) */
/* two words at the top of RAM, outside both programs' RAM, that live through a reset: the
 * application leaves BOOT_STAY there for the loader (both link scripts stop 16 short of 10 K) */
#define BOOT_WORDS ((volatile uint32_t *)(0x20000000u + 10u * 1024u - 16u))

void clock_init(void);
uint32_t now_us(void);
void hw_bus_init(void);                     /* transceiver on, pair to CAN; next board still off */
void hw_next(int on);                       /* the next board's 5 V */
void hw_release(uint16_t ms, int cycle);    /* LC_RELEASE: never returns */
void hw_can_init(const uint16_t ids[4]);    /* the 4 standard ids the filter lets in */
void hw_can_filter(const uint16_t ids[4]);
int hw_mailbox_free(void);
int hw_tx_idle(void);                       /* every mailbox empty: all sent */
void hw_can_send(const lever_frame_t *f);
int hw_can_take(lever_frame_t *f);
int hw_erase(uint32_t off, uint32_t n);     /* offsets from the flash base, 256-aligned */
int hw_write(uint32_t off, const uint32_t *page256);
int hw_cfg_save(const lever_cfg_t *c);
uint32_t hw_uid(void);
#endif
