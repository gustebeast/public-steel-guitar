/* The lever board's logic: see lever.h. Pure C, no hardware, no library calls. */
#include "lever.h"

uint32_t lever_crc32(const void *p, uint32_t n)
{   /* the zlib / binascii.crc32 one */
    const uint8_t *b = p;
    uint32_t c = 0xFFFFFFFFu;
    while (n--) {
        c ^= *b++;
        for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1u)));
    }
    return ~c;
}

int lever_cfg_ok(const lever_cfg_t *c)
{
    return c->magic == CFG_MAGIC && c->crc == lever_crc32(c, sizeof *c - 4)
           && c->rest < 16384 && c->full < 16384 && (c->slot < SLOTS || c->slot == SLOT_NONE);
}

void lever_cfg_seal(lever_cfg_t *c)
{
    c->magic = CFG_MAGIC;
    c->crc = lever_crc32(c, sizeof *c - 4);
}

static int32_t s14(int32_t d)               /* an angle difference, -8192 .. 8191 */
{
    d &= 0x3FFF;
    return d >= 0x2000 ? d - 0x4000 : d;
}

void lever_init(lever_t *l, const lever_cfg_t *stored, uint32_t uid, uint32_t now_us)
{
    uint8_t *z = (uint8_t *)l;
    for (uint32_t i = 0; i < sizeof *l; i++) z[i] = 0;
    if (stored && lever_cfg_ok(stored)) {
        l->cfg = *stored;
    } else {
        l->cfg.slot = SLOT_NONE;
        l->cfg.mglt = l->cfg.mght = 0xFF;
        lever_cfg_seal(&l->cfg);
    }
    l->uid = uid;
    l->hello_now = 1;
    l->t_pos = l->t_diag = l->t_hello = now_us;
}

static int32_t med3(int32_t a, int32_t b, int32_t c)
{
    if (a > b) { int32_t t = a; a = b; b = t; }
    return c < a ? a : (c > b ? b : c);
}

void lever_sample(lever_t *l, uint16_t raw14)
{
    raw14 &= 0x3FFF;
    if (!l->n) {
        l->acc[0] = l->acc[1] = l->acc[2] = raw14;
        l->filt = (int32_t)raw14 << 4;
        l->prev_raw = raw14;
        l->n = 1;
        return;
    }
    /* unwrapped: a lever never moves half a turn in a millisecond */
    int32_t a = l->acc[2] + s14((int32_t)raw14 - l->prev_raw);
    l->prev_raw = raw14;
    l->acc[0] = l->acc[1]; l->acc[1] = l->acc[2]; l->acc[2] = a;
    if (l->n < 3) l->n++;
    /* median of three throws out a single bad read (an SPI glitch), then a first-order filter,
     * a quarter per sample: about 4 ms at SAMPLE_US, against a motor that takes 40 */
    int32_t m = l->n < 3 ? a : med3(l->acc[0], l->acc[1], l->acc[2]);
    l->filt += ((m << 4) - l->filt) / 4;
    if (l->acc[2] > (1 << 20) || l->acc[2] < -(1 << 20)) {     /* turns: never, but bounded */
        int32_t k = l->acc[2] & ~0x3FFF;
        for (int i = 0; i < 3; i++) l->acc[i] -= k;
        l->filt -= k << 4;
    }
}

void lever_field(lever_t *l, uint8_t mgh_mgl) { l->field = mgh_mgl & 0xC0; }

uint16_t lever_raw(const lever_t *l) { return (uint16_t)(((l->filt + 8) >> 4) & 0x3FFF); }

/* filtered angle minus rest, 1/16 counts, signed; *span16 its full travel, positive */
static int32_t travel(const lever_t *l, int32_t *span16)
{
    int32_t span = s14((int32_t)l->cfg.full - l->cfg.rest);
    int32_t d = (l->filt - ((int32_t)l->cfg.rest << 4)) & 0x3FFFF;
    if (d >= 0x20000) d -= 0x40000;
    if (span < 0) { span = -span; d = -d; }
    *span16 = span << 4;
    return d;
}

static int calibrated(const lever_t *l)
{
    int32_t span = s14((int32_t)l->cfg.full - l->cfg.rest);
    return l->n && lever_cfg_ok(&l->cfg) && (span >= (int32_t)MIN_SPAN || -span >= (int32_t)MIN_SPAN);
}

uint16_t lever_pos(const lever_t *l)
{
    if (!calibrated(l)) return POS_NONE;
    int32_t span16, d = travel(l, &span16);
    if (d <= 0) return 0;
    if (d >= span16) return POS_FULL;
    return (uint16_t)((uint32_t)d * POS_FULL / (uint32_t)span16);  /* < 2^17 * 2^15: fits */
}

uint8_t lever_status(const lever_t *l)
{
    uint8_t s = (l->field & 0x40 ? LV_MGL : 0) | (l->field & 0x80 ? LV_MGH : 0)
                | (l->unsaved ? LV_UNSAVED : 0);
    if (!calibrated(l)) return s | LV_UNCAL;
    int32_t span16, d = travel(l, &span16);
    if (d < -span16 / 32 || d > span16 + span16 / 32) s |= LV_OUTSIDE;
    return s;
}

static void put16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }

static void hello(lever_t *l, lever_frame_t *o)
{
    o->id = ID_HELLO | (l->uid & 0xFFFFFFu); o->ext = 1; o->len = 8;
    put16(o->d, (uint16_t)l->uid); put16(o->d + 2, (uint16_t)(l->uid >> 16));
    o->d[4] = l->cfg.slot; o->d[5] = LEVER_VERSION; o->d[6] = l->mode; o->d[7] = lever_status(l);
}

int lever_poll(lever_t *l, uint32_t now, lever_frame_t *o)
{
    if (l->reply_n) { *o = l->reply; l->reply_n = 0; return 1; }
    uint8_t slot = l->cfg.slot;
    if (slot < SLOTS && l->n) {
        uint16_t pos = lever_pos(l);
        uint8_t st = lever_status(l);
        uint32_t since = now - l->t_pos;
        uint16_t moved = pos > l->sent_pos ? pos - l->sent_pos : l->sent_pos - pos;
        int changed = moved >= DEADBAND || st != l->sent_status
                      || (pos == POS_NONE) != (l->sent_pos == POS_NONE);
        if (since >= TX_IDLE_US || (since >= TX_MIN_US && changed)) {
            o->id = ID_POS + slot; o->ext = 0; o->len = 4;
            put16(o->d, pos); o->d[2] = st; o->d[3] = l->seq++;
            l->t_pos = now; l->sent_pos = pos; l->sent_status = st;
            return 1;
        }
        if (now - l->t_diag >= DIAG_US) {
            o->id = ID_DIAG + slot; o->ext = 0; o->len = 8;
            put16(o->d, lever_raw(l)); put16(o->d + 2, l->cfg.rest); put16(o->d + 4, l->cfg.full);
            o->d[6] = l->field; o->d[7] = LEVER_VERSION;
            l->t_diag = now;
            return 1;
        }
    }
    if (l->hello_now || (slot == SLOT_NONE && now - l->t_hello >= HELLO_US)) {
        hello(l, o);
        l->hello_now = 0; l->t_hello = now;
        return 1;
    }
    return 0;
}

static void changed(lever_t *l) { lever_cfg_seal(&l->cfg); l->unsaved = 1; }

void lever_rx(lever_t *l, const lever_frame_t *in)
{
    if (in->ext || !in->len) return;
    const uint8_t *d = in->d;
    if (in->id == ID_ALL) {
        if (d[0] == LC_HELLO) l->hello_now = 1;
        uint32_t uid = d[1] | (uint32_t)d[2] << 8 | (uint32_t)d[3] << 16 | (uint32_t)d[4] << 24;
        if (d[0] == LC_SLOT && in->len >= 6 && uid == l->uid && (d[5] < SLOTS || d[5] == SLOT_NONE)) {
            l->cfg.slot = d[5]; changed(l);
            l->want_save = 1; l->hello_now = 1;
        }
        return;
    }
    if (l->cfg.slot >= SLOTS || in->id != ID_CMD + l->cfg.slot) return;
    uint8_t ok = 1;
    l->reply.id = ID_REPLY + l->cfg.slot;   /* the slot it was asked on, even by LC_SLOT */
    switch (d[0]) {
    case LC_REST: ok = l->n != 0; if (ok) { l->cfg.rest = lever_raw(l); changed(l); } break;
    case LC_FULL: ok = l->n != 0; if (ok) { l->cfg.full = lever_raw(l); changed(l); } break;
    case LC_CAL:
        ok = in->len >= 5;
        if (ok) {
            l->cfg.rest = (uint16_t)((d[1] | d[2] << 8) & 0x3FFF);
            l->cfg.full = (uint16_t)((d[3] | d[4] << 8) & 0x3FFF);
            changed(l);
        }
        break;
    case LC_SAVE: l->want_save = 1; break;
    case LC_SLOT:
        ok = in->len >= 2 && d[1] < SLOTS;
        if (ok) { l->cfg.slot = d[1]; changed(l); }
        break;
    case LC_THRESH:
        ok = in->len >= 3;
        if (ok) { l->cfg.mglt = d[1] & 7; l->cfg.mght = d[2] & 7; changed(l); l->want_thresh = 1; }
        break;
    case LC_HELLO: l->hello_now = 1; break;
    case LC_LOADER: l->want_loader = 1; break;
    default: ok = 0;
    }
    l->reply.ext = 0; l->reply.len = 2; l->reply.d[0] = d[0]; l->reply.d[1] = ok;
    l->reply_n = 1;
}
