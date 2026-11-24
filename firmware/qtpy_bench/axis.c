#include "axis.h"

static uint32_t isqrt64(uint64_t v)
{
    uint64_t r = 0, b = (uint64_t)1 << 62;
    while (b > v)
        b >>= 2;
    while (b) {
        if (v >= r + b) {
            v -= r + b;
            r = (r >> 1) + b;
        } else {
            r >>= 1;
        }
        b >>= 2;
    }
    return (uint32_t)r;
}

static uint32_t clamp_c(uint32_t c, uint32_t cmin)
{
    if (c < cmin)
        c = cmin;
    if (c > (AXIS_CMAX << 8))
        c = AXIS_CMAX << 8;
    return c;
}

uint32_t axis_start(axis_t *a, int32_t target, uint32_t vmax, uint32_t acc)
{
    int32_t d = target - a->pos;
    a->dir = d < 0 ? -1 : 1;
    a->moving = 0;
    a->done = 0;
    if (d == 0 || vmax == 0 || acc == 0)
        return 0;
    a->target = target;
    a->total = (uint32_t)(d < 0 ? -d : d);

    uint32_t cmin = AXIS_TICK_HZ / vmax;
    if (cmin < AXIS_CMIN)
        cmin = AXIS_CMIN;
    if (cmin > AXIS_CMAX)
        cmin = AXIS_CMAX;
    a->cmin = cmin << 8;

    /* steps to reach vmax at acc; at least one, so a move always has a first interval */
    uint64_t nacc = ((uint64_t)vmax * vmax) / (2u * (uint64_t)acc);
    if (nacc < 1)
        nacc = 1;
    uint32_t half = a->total / 2;
    a->acc_end = nacc < half ? (uint32_t)nacc : half;
    a->dec_start = a->total - a->acc_end;

    /* c0 = 0.676 F sqrt(2 / acc): AVR446's first interval, with its 0.676 correction */
    uint64_t f = AXIS_TICK_HZ;
    uint32_t c0 = (uint32_t)(((uint64_t)isqrt64((2u * f * f) / acc) * 676u) / 1000u);
    if (c0 > AXIS_CMAX)
        c0 = AXIS_CMAX;
    a->c = clamp_c(c0 << 8, a->cmin);
    a->moving = 1;
    return a->c >> 8;
}

uint32_t axis_next(axis_t *a)
{
    if (!a->moving)
        return 0;
    a->pos += a->dir;
    a->done++;
    if (a->done >= a->total) {
        a->moving = 0;
        return 0;
    }
    uint32_t n = a->done;
    if (n < a->acc_end) {
        /* c_n = c_{n-1} - 2 c_{n-1} / (4n + 1) */
        a->c = clamp_c(a->c - (2u * a->c) / (4u * n + 1u), a->cmin);
    } else if (n < a->dec_start) {
        a->c = a->cmin;
    } else {
        /* the same recurrence run backwards over the r steps left: c + 2c / (4r - 1) */
        uint32_t r = a->total - n;
        a->c = clamp_c(a->c + (2u * a->c) / (4u * r - 1u), a->cmin);
    }
    return a->c >> 8;
}

void axis_halt(axis_t *a)
{
    a->moving = 0;
    a->target = a->pos;
}
