#ifndef FRAME_H
#define FRAME_H
/* R2's link framing, on the wire between U7 (CH340C) and USART1. Pure C, no hardware: the Pi's
 * tests compile this same file natively (bench/tests/test_frames.py).
 *
 * A UART has no CRC where USB had one, and a bit flipped in a "Q" line is a different motor
 * move. So each frame is   0x00  COBS(payload, CRC-16)  0x00   and a frame whose CRC fails is
 * dropped and counted. CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF), high byte first. The
 * leading 0x00 ends whatever noise came before (a reset, a plug), so it cannot spoil the frame.
 *
 * A frame carries WHOLE lines (or the loader's "W" line and its page): the sender never splits
 * one, so a dropped frame loses lines and never joins two halves into a third.
 * bench/publicbench/frames.py is the host's copy of all of this. */
#include <stdint.h>

#define FRAME_MAX 300u                          /* payload: "W ..." + a 256-byte page fits */
#define FRAME_WIRE (FRAME_MAX + 2u + FRAME_MAX / 254u + 1u + 2u)   /* CRC, COBS, both 0x00 */

uint16_t frame_crc(const uint8_t *p, uint32_t n);

/* payload -> wire bytes in out (FRAME_WIRE long); returns how many, 0 if n > FRAME_MAX */
uint32_t frame_encode(const uint8_t *p, uint32_t n, uint8_t *out);

typedef struct {
    uint8_t buf[FRAME_MAX + 2u + FRAME_MAX / 254u + 1u];   /* one frame, still COBS-encoded */
    uint32_t n;
    uint8_t over;                                          /* the frame ran past buf */
    uint32_t bad;                                          /* frames dropped: CRC, COBS, length */
} frame_rx_t;

/* Feed one wire byte. Returns the payload length when it completes a good frame (the payload
 * is then at out, FRAME_MAX long), else -1. */
int frame_feed(frame_rx_t *r, uint8_t c, uint8_t *out);
#endif
