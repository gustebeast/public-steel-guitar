/* The lever board's CAN loader protocol: see ldr.h. Pure C, no hardware, no library calls. */
#include "ldr.h"

static uint32_t get32(const uint8_t *p)
{
    return p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

int ldr_app_ok(const uint8_t *flash)
{
    const uint8_t *r = flash + REC_AT;
    uint32_t len = get32(r + 4), crc = get32(r + 8);
    return get32(r) == REC_MAGIC && get32(r + 12) == ~crc && len && len <= APP_MAX
           && lever_crc32(flash + APP_AT, len) == crc;
}

void ldr_init(ldr_t *b, const uint8_t *flash, int (*erase)(uint32_t, uint32_t),
              int (*write)(uint32_t, const uint32_t *), uint8_t slot)
{
    uint8_t *z = (uint8_t *)b;
    for (uint32_t i = 0; i < sizeof *b; i++) z[i] = 0;
    b->flash = flash; b->erase = erase; b->write = write; b->slot = slot;
}

static void say(ldr_t *b, uint8_t op, uint8_t ok, uint8_t n, const uint8_t *more)
{
    b->reply.id = ID_LDR_R + b->slot; b->reply.ext = 0; b->reply.len = (uint8_t)(2 + n);
    b->reply.d[0] = op; b->reply.d[1] = ok;
    for (uint8_t i = 0; i < n; i++) b->reply.d[2 + i] = more[i];
    b->reply_n = 1;
}

static int same(const uint8_t *a, const uint32_t *w, uint32_t n)
{
    const uint8_t *c = (const uint8_t *)w;
    for (uint32_t i = 0; i < n; i++) if (a[i] != c[i]) return 0;
    return 1;
}

void ldr_rx(ldr_t *b, const lever_frame_t *in)
{
    if (in->ext || b->slot >= SLOTS) return;
    const uint8_t *d = in->d;
    if (in->id == ID_LDR_D + b->slot) {
        b->heard = 1;
        if (!b->paging || in->len != 8) return;
        uint8_t *p = (uint8_t *)b->page + 8u * b->got;
        for (int i = 0; i < 8; i++) p[i] = d[i];
        if (++b->got < LDR_PAGE / 8) return;
        b->paging = 0;
        uint32_t off = APP_AT + (uint32_t)b->page_no * LDR_PAGE;
        uint8_t no[2] = { (uint8_t)b->page_no, (uint8_t)(b->page_no >> 8) };
        int ok = lever_crc32(b->page, LDR_PAGE) == b->page_crc && b->write(off, b->page)
                 && same(b->flash + off, b->page, LDR_PAGE);
        say(b, 'W', (uint8_t)ok, 2, no);
        return;
    }
    if (in->id != ID_LDR + b->slot || !in->len) return;
    b->heard = 1;
    b->paging = 0;                                  /* any command ends a page in progress */
    uint32_t a = in->len >= 5 ? get32(d + 1) : 0;
    switch (d[0]) {
    case 'I': {
        uint8_t more[2] = { LDR_VERSION, (uint8_t)ldr_app_ok(b->flash) };
        say(b, 'I', 1, 2, more);
        break; }
    case 'E': {
        int ok = in->len >= 5 && a && a <= APP_MAX;
        if (ok) ok = b->erase(REC_AT, LDR_PAGE)
                     && b->erase(APP_AT, (a + LDR_PAGE - 1) / LDR_PAGE * LDR_PAGE);
        say(b, 'E', (uint8_t)ok, 0, 0);
        break; }
    case 'W': {
        uint16_t no = (uint16_t)(d[1] | d[2] << 8);
        if (in->len >= 7 && no < APP_MAX / LDR_PAGE) {
            b->paging = 1; b->got = 0; b->page_no = no; b->page_crc = get32(d + 3);
        } else {
            uint8_t nb[2] = { d[1], d[2] };
            say(b, 'W', 0, 2, nb);
        }
        break; }
    case 'C': {
        uint32_t len = d[1] | (uint32_t)d[2] << 8 | (uint32_t)d[3] << 16;
        uint32_t crc = in->len >= 8 ? get32(d + 4) : 0;
        int ok = in->len >= 8 && len && len <= APP_MAX && lever_crc32(b->flash + APP_AT, len) == crc;
        if (ok) {
            for (uint32_t i = 0; i < LDR_PAGE / 4; i++) b->page[i] = 0xFFFFFFFFu;
            b->page[0] = REC_MAGIC; b->page[1] = len; b->page[2] = crc; b->page[3] = ~crc;
            ok = b->write(REC_AT, b->page) && ldr_app_ok(b->flash);
        }
        say(b, 'C', (uint8_t)ok, 0, 0);
        break; }
    case 'G':
        say(b, 'G', 1, 0, 0);
        b->go = 1;
        break;
    default:
        say(b, d[0], 0, 0, 0);
    }
}

int ldr_poll(ldr_t *b, lever_frame_t *out)
{
    if (!b->reply_n) return 0;
    *out = b->reply; b->reply_n = 0;
    return 1;
}
