/* R2's link framing: see frame.h. */
#include "frame.h"

uint16_t frame_crc(const uint8_t *p, uint32_t n)
{
    uint16_t c = 0xFFFF;
    while (n--) {
        c ^= (uint16_t)(*p++ << 8);
        for (int k = 0; k < 8; k++) c = (uint16_t)((c & 0x8000) ? (c << 1) ^ 0x1021 : c << 1);
    }
    return c;
}

uint32_t frame_encode(const uint8_t *p, uint32_t n, uint8_t *out)
{
    if (n > FRAME_MAX) return 0;
    uint16_t crc = frame_crc(p, n);
    uint32_t o = 0, code_at, total = n + 2;
    out[o++] = 0;
    code_at = o++;
    uint8_t code = 1;
    for (uint32_t i = 0; i < total; i++) {
        uint8_t c = i < n ? p[i] : (i == n ? (uint8_t)(crc >> 8) : (uint8_t)crc);
        if (c == 0) {
            out[code_at] = code; code_at = o++; code = 1;
        } else {
            out[o++] = c;
            if (++code == 0xFF) { out[code_at] = code; code_at = o++; code = 1; }
        }
    }
    out[code_at] = code;
    out[o++] = 0;
    return o;
}

static int decode(const frame_rx_t *r, uint8_t *out)
{   /* COBS back to payload + CRC, then check it */
    uint32_t i = 0, o = 0;
    while (i < r->n) {
        uint8_t code = r->buf[i++];
        if (code == 0 || i + code - 1 > r->n) return -1;
        for (uint8_t k = 1; k < code; k++) {
            if (o >= FRAME_MAX + 2) return -1;
            out[o++] = r->buf[i++];
        }
        if (code != 0xFF && i < r->n) {
            if (o >= FRAME_MAX + 2) return -1;
            out[o++] = 0;
        }
    }
    if (o < 2) return -1;
    uint16_t want = (uint16_t)(out[o - 2] << 8 | out[o - 1]);
    return frame_crc(out, o - 2) == want ? (int)(o - 2) : -1;
}

int frame_feed(frame_rx_t *r, uint8_t c, uint8_t *out)
{
    if (c != 0) {
        if (r->n < sizeof r->buf) r->buf[r->n++] = c;
        else r->over = 1;
        return -1;
    }
    int got = -1;
    if (r->n) {                                 /* 00 00 is no frame, and not an error */
        static uint8_t tmp[FRAME_MAX + 2];
        got = r->over ? -1 : decode(r, tmp);
        if (got < 0) r->bad++;
        else for (int i = 0; i < got; i++) out[i] = tmp[i];
    }
    r->n = 0; r->over = 0;
    return got;
}
