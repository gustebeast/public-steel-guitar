/* ma730.h -- the lever board's angle sensor, MPS MA730GQ-Z, on SPI1 (elec/lever_sensor.py).
 *
 * Wiring (lever_sensor U3 = CH32V203G6U6, U4 = MA730):
 *   PA5 SPI1_SCK  -> SCLK (12)      PA6 SPI1_MISO <- MISO (7)
 *   PA7 SPI1_MOSI -> MOSI (4)       PB5 GPIO      -> CS (5), idles high on the sensor's pull-up
 *
 * Everything below is off MPS's MA730 datasheet rev 1.1 (8/8/2022):
 *   p.11  SPI mode 0 or 3, detected by the part; 25 MHz at most
 *   p.12  CS falling to the first SCLK edge 80 ns; 150 ns idle between angle reads, 750 ns before
 *         and after a register read, 20 ms after a register write (non-volatile memory)
 *   p.13  angle read: one 16-bit frame, MOSI 0, MISO = angle MSB first, 14 bits used
 *   p.14  register read: 010 + 5-bit address + 0x00, the value in the NEXT frame's high byte
 *   p.16  register write (fig. 14): 100 + address + value, 20 ms, then the stored value in the
 *         next frame's high byte
 *   p.18  register 6 = MGLT(7:5) MGHT(4:2), factory 0x1C; register 27 = MGH(7) MGL(6)
 *   p.21  the 3-bit field thresholds, rising / falling, at VDD 3.3 V:
 *         000 26/20  001 41/35  010 56/50  011 70/64  100 84/78  101 98/92  110 112/106  111 126/120 mT
 *
 * Nothing is burned into the part by this driver unless ma730_thresholds() is asked for a value
 * the part does not already hold: zero and direction live in the MCU, as they did for the MT6701.
 * The caller supplies Delay_Us / Delay_Ms (as firmware/motor_ctrl/link.c does).
 */
#ifndef MA730_H
#define MA730_H

#include <stdint.h>

#define MA730_REG_THRESH   6        /* MGLT(7:5) MGHT(4:2) */
#define MA730_REG_FLAGS    27       /* MGH(7) MGL(6) */
#define MA730_MGH          0x80     /* field over MGHT: magnet too close, or the wrong magnet */
#define MA730_MGL          0x40     /* field under MGLT: magnet missing, too far, or cracked */

void ma730_init(void);                       /* SPI1 + PB5, mode 3, 6 MHz at a 48 MHz PCLK2 */
uint16_t ma730_angle(void);                  /* 0 .. 16383 for one turn, clockwise seen from the top */
uint8_t ma730_read(uint8_t reg);             /* one register (5-bit address) */
uint8_t ma730_field(void);                   /* MA730_MGH | MA730_MGL, 0 when the field is in range */
/* Set MGLT / MGHT (3-bit codes, table above). Writes only what differs, because each write goes
 * to non-volatile memory and takes 20 ms. Returns the register as read back. */
uint8_t ma730_thresholds(uint8_t mglt, uint8_t mght);

void Delay_Us(uint32_t n);
void Delay_Ms(uint32_t n);

#endif
