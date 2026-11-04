/* Lever positions -> motor targets: see play.h. Pure C, no hardware, no library calls. */
#include "play.h"

uint32_t play_crc32(const void *d, uint32_t n)
{   /* the zlib / binascii.crc32 one, as lever.c's */
    const uint8_t *b = d;
    uint32_t c = 0xFFFFFFFFu;
    while (n--) {
        c ^= *b++;
        for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1u)));
    }
    return ~c;
}

int play_table_ok(const play_table_t *t)
{
    if (!t || t->magic != PLAY_MAGIC || t->version != PLAY_VERSION || t->rpm > 3000
            || t->crc != play_crc32(t, sizeof *t - 4))
        return 0;
    for (uint32_t s = 0; s < PLAY_STRINGS; s++)
        if (t->curve[s][(0 - KNOT_LO) / KNOT_CENTS] != 0) return 0;     /* 0 cents is the base */
    return 1;
}

void play_init(play_t *p, const play_table_t *t)
{
    uint8_t *z = (uint8_t *)p;
    for (uint32_t i = 0; i < sizeof *p; i++) z[i] = 0;
    if (play_table_ok(t)) { p->t = *t; p->ok = 1; p->on = 1; }
}

int play_load(play_t *p, const play_table_t *t)
{
    if (!play_table_ok(t)) return 0;
    p->t = *t; p->ok = 1; p->dirty = 1;
    return 1;
}

int32_t play_counts(const play_table_t *t, uint8_t s, int32_t cents)
{
    const int32_t *c = t->curve[s];
    int32_t x = cents - KNOT_LO;
    if (x <= 0) return c[0];
    int32_t k = x / KNOT_CENTS;
    if (k >= (int32_t)PLAY_KNOTS - 1) return c[PLAY_KNOTS - 1];
    return c[k] + (c[k + 1] - c[k]) * (x % KNOT_CENTS) / KNOT_CENTS;
}

int32_t play_cents(const play_t *p, uint8_t s)
{
    int32_t up = 0, down = 0;
    for (uint32_t c = 0; c < PLAY_SLOTS; c++) {
        int32_t v = (int32_t)p->pos[c] * p->t.cents[c][s] / (int32_t)PLAY_POS_FULL;
        if (v > up) up = v;
        if (v < down) down = v;
    }
    return up + down;
}

static int32_t i48_to_32(const uint8_t *b)
{   /* big-endian int48, kept to its low 32 bits: a reading past +-131000 turns is not a string */
    return (int32_t)((uint32_t)b[2] << 24 | (uint32_t)b[3] << 16 | (uint32_t)b[4] << 8 | b[5]);
}

void play_rx(play_t *p, uint8_t bus, const play_frame_t *f, uint32_t now)
{
    if (!p->ok || f->ext) return;
    if (bus == 1) {
        uint32_t slot = f->id - PLAY_POS_ID;
        if (slot >= PLAY_SLOTS || f->len < 2) return;
        uint16_t v = (uint16_t)(f->d[0] | f->d[1] << 8);
        if (v > PLAY_POS_FULL) v = 0;                   /* 0xFFFF: uncalibrated, so at rest */
        p->heard[slot] = now;
        if (v != p->pos[slot]) { p->pos[slot] = v; p->dirty = 1; }
        return;
    }
    if (f->len < 3) return;
    uint8_t sum = (uint8_t)f->id;
    for (uint8_t i = 0; i + 1 < f->len; i++) sum = (uint8_t)(sum + f->d[i]);
    if (sum != f->d[f->len - 1]) return;
    for (uint32_t s = 0; s < PLAY_STRINGS; s++) {
        if (!p->t.motor[s] || p->t.motor[s] != f->id) continue;
        if (f->d[0] == SV_READ_ENC && f->len == 8 && p->state[s] == 0) {
            p->base[s] = i48_to_32(f->d + 1);
            p->state[s] = 1; p->told[s] = 0;
        } else if (f->d[0] == SV_ENABLE && f->d[1] == 1 && p->state[s] == 1) {
            p->state[s] = 2; p->sent[s] = 0; p->told[s] = 1; p->dirty = 1;
        }
    }
}

void play_rebase(play_t *p)
{
    for (uint32_t s = 0; s < PLAY_STRINGS; s++) { p->state[s] = 0; p->told[s] = 0; }
}

static int frame(play_t *p, uint8_t s, uint32_t now, play_frame_t *o, uint8_t n, const uint8_t *body)
{
    o->id = p->t.motor[s]; o->ext = 0; o->len = (uint8_t)(n + 1);
    uint8_t sum = (uint8_t)o->id;
    for (uint8_t i = 0; i < n; i++) { o->d[i] = body[i]; sum = (uint8_t)(sum + body[i]); }
    o->d[n] = sum;
    p->last[s] = now;
    return 1;
}

int play_poll(play_t *p, uint32_t now, play_frame_t *o)
{
    if (!p->ok || !p->on) return 0;
    for (uint32_t c = 0; c < PLAY_SLOTS; c++)
        if (p->pos[c] && now - p->heard[c] > PLAY_LOST_US) { p->pos[c] = 0; p->dirty = 1; }
    if (p->dirty) {
        p->dirty = 0;
        for (uint8_t s = 0; s < PLAY_STRINGS; s++) p->target[s] = play_counts(&p->t, s, play_cents(p, s));
    }
    for (uint32_t k = 0; k < PLAY_STRINGS; k++) {
        uint8_t s = (uint8_t)((p->rr + k) % PLAY_STRINGS);
        if (!p->t.motor[s]) continue;
        int due = !p->told[s] || now - p->last[s] >= PLAY_ASK_US;
        if (p->state[s] == 0 && due) {
            uint8_t b[1] = { SV_READ_ENC };
            p->told[s] = 1; p->rr = (uint8_t)(s + 1);
            return frame(p, s, now, o, 1, b);
        }
        if (p->state[s] == 1 && due) {
            uint8_t b[2] = { SV_ENABLE, 1 };
            p->told[s] = 1; p->rr = (uint8_t)(s + 1);
            return frame(p, s, now, o, 2, b);
        }
        if (p->state[s] != 2) continue;
        int32_t d = p->target[s] - p->sent[s];
        if ((d > PLAY_DEADBAND || d < -PLAY_DEADBAND || (d && !p->target[s]))
                && now - p->last[s] >= p->t.min_us) {
            int32_t c = p->base[s] + p->target[s];
            if (c < -0x800000 || c > 0x7FFFFF) continue;    /* F5 carries 24 bits */
            uint8_t b[7] = { SV_MOVE_ABS, (uint8_t)(p->t.rpm >> 8), (uint8_t)p->t.rpm, p->t.acc,
                             (uint8_t)(c >> 16), (uint8_t)(c >> 8), (uint8_t)c };
            p->sent[s] = p->target[s]; p->moves++; p->rr = (uint8_t)(s + 1);
            return frame(p, s, now, o, 7, b);
        }
    }
    return 0;
}
