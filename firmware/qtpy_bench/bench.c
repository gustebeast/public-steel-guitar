#include "bench.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "tmc.h"

#define MAXARGS 6

void bench_init(bench_t *b, const bench_ops_t *ops, uint32_t rsense_mohm)
{
    memset(b, 0, sizeof *b);
    b->ops = *ops;
    b->mres = 6;                /* 1/4 step at the input, interpolated to 1/256 */
    b->rsense = rsense_mohm;
    b->irun = tmc_cs_for_ma(500, rsense_mohm);
    b->ihold = 0;               /* freewheel at rest until told otherwise */
    b->iholddelay = 4;
}

uint32_t bench_step_isr(bench_t *b)
{
    return axis_next(&b->ax);
}

typedef struct {
    int32_t pos, target;
    int moving;
} snap_t;

static snap_t snap(bench_t *b)
{
    snap_t s;
    b->ops.lock(b->ops.ctx);
    s.pos = b->ax.pos;
    s.target = b->ax.target;
    s.moving = b->ax.moving;
    b->ops.unlock(b->ops.ctx);
    return s;
}

static int num(const char *s, long *v)
{
    char *end;
    if (!s)
        return 0;
    *v = strtol(s, &end, 0);
    return *end == 0 && end != s;
}

static int unum(const char *s, uint32_t *v)
{
    char *end;
    if (!s || *s == '-')
        return 0;
    *v = (uint32_t)strtoul(s, &end, 0);
    return *end == 0 && end != s;
}

static int wr(bench_t *b, uint8_t reg, uint32_t v)
{
    return b->ops.tmc_write(b->ops.ctx, reg, v);
}

static int start_move(bench_t *b, int32_t target, uint32_t v, uint32_t a, char *out, int n)
{
    if (snap(b).moving)
        return snprintf(out, n, "err busy");
    uint32_t first = axis_start(&b->ax, target, v, a);
    if (!first)
        return snprintf(out, n, "ok steps=0");
    b->ops.step_start(b->ops.ctx, b->ax.dir, first);
    return snprintf(out, n, "ok steps=%lu", (unsigned long)b->ax.total);
}

int bench_line(bench_t *b, const char *line, char *out, int n)
{
    char buf[96];
    char *av[MAXARGS];
    int ac = 0;
    strncpy(buf, line, sizeof buf - 1);
    buf[sizeof buf - 1] = 0;
    for (char *p = strtok(buf, " \t\r\n"); p && ac < MAXARGS; p = strtok(NULL, " \t\r\n"))
        av[ac++] = p;
    if (ac == 0)
        return snprintf(out, n, "err empty");
    const char *c = av[0];
    long l1;
    uint32_t u1, u2, u3, v;

    if (!strcmp(c, "id"))
        return snprintf(out, n, "ok %s tick=%lu", BENCH_VERSION, (unsigned long)AXIS_TICK_HZ);

    if (!strcmp(c, "en") && ac == 2 && num(av[1], &l1)) {
        b->enabled = l1 != 0;
        b->ops.enable(b->ops.ctx, b->enabled);
        return snprintf(out, n, "ok en=%d", b->enabled);
    }

    if (!strcmp(c, "r") && ac == 2 && unum(av[1], &u1) && u1 < 0x80) {
        int e = b->ops.tmc_read(b->ops.ctx, (uint8_t)u1, &v);
        if (e)
            return snprintf(out, n, "err uart %d", e);
        return snprintf(out, n, "ok 0x%02lx=0x%08lx", (unsigned long)u1, (unsigned long)v);
    }

    if (!strcmp(c, "w") && ac == 3 && unum(av[1], &u1) && u1 < 0x80 && unum(av[2], &u2)) {
        int e = wr(b, (uint8_t)u1, u2);
        return e ? snprintf(out, n, "err uart %d", e) : snprintf(out, n, "ok");
    }

    /* init [steps-per-full-step]: GCONF, GSTAT cleared, CHOPCONF, IHOLD_IRUN, TPOWERDOWN, and
     * IFCNT before and after, which counts the writes the driver took (p21) */
    if (!strcmp(c, "init") && ac <= 2) {
        int code = b->mres;
        if (ac == 2 && !(unum(av[1], &u1) && (code = tmc_mres_code(u1)) >= 0))
            return snprintf(out, n, "err usteps");
        if (snap(b).moving)
            return snprintf(out, n, "err busy");
        uint32_t if0, if1;
        if (b->ops.tmc_read(b->ops.ctx, TMC_IFCNT, &if0))
            return snprintf(out, n, "err uart no reply");
        if (wr(b, TMC_GCONF, TMC_GCONF_BENCH) || wr(b, TMC_GSTAT, 7) ||
            wr(b, TMC_CHOPCONF, tmc_chopconf(code, 1)) ||
            wr(b, TMC_IHOLD_IRUN, tmc_ihold_irun(b->ihold, b->irun, b->iholddelay)) ||
            wr(b, TMC_TPOWERDOWN, 20) || b->ops.tmc_read(b->ops.ctx, TMC_IFCNT, &if1))
            return snprintf(out, n, "err uart");
        if (code != b->mres) {
            b->ops.lock(b->ops.ctx);
            b->ax.pos = b->ax.target = 0;   /* the unit changed: positions restart at 0 */
            b->ops.unlock(b->ops.ctx);
            b->mres = code;
        }
        return snprintf(out, n, "ok writes=%lu usteps=%u", (unsigned long)((if1 - if0) & 0xFF),
                        256u >> b->mres);
    }

    /* cur run_mA hold_mA [holddelay]: RMS currents, rounded to the driver's 1/32 scale */
    if (!strcmp(c, "cur") && (ac == 3 || ac == 4) && unum(av[1], &u1) && unum(av[2], &u2)) {
        u3 = b->iholddelay;
        if (ac == 4 && !(unum(av[3], &u3) && u3 < 16))
            return snprintf(out, n, "err holddelay");
        b->irun = tmc_cs_for_ma(u1, b->rsense);
        b->ihold = u2 ? tmc_cs_for_ma(u2, b->rsense) : 0;
        b->iholddelay = u3;
        int e = wr(b, TMC_IHOLD_IRUN, tmc_ihold_irun(b->ihold, b->irun, b->iholddelay));
        if (e)
            return snprintf(out, n, "err uart %d", e);
        return snprintf(out, n, "ok irun=%lu run_mA=%lu ihold=%lu hold_mA=%lu",
                        (unsigned long)b->irun, (unsigned long)tmc_ma_for_cs(b->irun, b->rsense),
                        (unsigned long)b->ihold,
                        (unsigned long)(u2 ? tmc_ma_for_cs(b->ihold, b->rsense) : 0));
    }

    if (!strcmp(c, "go") && ac == 4 && num(av[1], &l1) && unum(av[2], &u2) && unum(av[3], &u3))
        return start_move(b, (int32_t)l1, u2, u3, out, n);

    if (!strcmp(c, "mv") && ac == 4 && num(av[1], &l1) && unum(av[2], &u2) && unum(av[3], &u3)) {
        snap_t s = snap(b);
        if (s.moving)
            return snprintf(out, n, "err busy");
        return start_move(b, s.pos + (int32_t)l1, u2, u3, out, n);
    }

    if (!strcmp(c, "halt")) {
        b->ops.lock(b->ops.ctx);
        b->ops.step_stop(b->ops.ctx);
        axis_halt(&b->ax);
        b->ops.unlock(b->ops.ctx);
        return snprintf(out, n, "ok pos=%ld", (long)b->ax.pos);
    }

    if (!strcmp(c, "zero")) {
        if (snap(b).moving)
            return snprintf(out, n, "err busy");
        b->ops.lock(b->ops.ctx);
        b->ax.pos = b->ax.target = 0;
        b->ops.unlock(b->ops.ctx);
        return snprintf(out, n, "ok");
    }

    if (!strcmp(c, "st")) {
        snap_t s = snap(b);
        return snprintf(out, n, "ok pos=%ld target=%ld moving=%d en=%d usteps=%u irun=%lu ihold=%lu",
                        (long)s.pos, (long)s.target, s.moving, b->enabled, 256u >> b->mres,
                        (unsigned long)b->irun, (unsigned long)b->ihold);
    }

    /* ms: the driver's MSCNT beside the steps this firmware has sent; the host checks
     * mscnt == mscnt0 +- pos * per (mod 1024) */
    if (!strcmp(c, "ms")) {
        snap_t s = snap(b);
        int e = b->ops.tmc_read(b->ops.ctx, TMC_MSCNT, &v);
        if (e)
            return snprintf(out, n, "err uart %d", e);
        snap_t s2 = snap(b);
        return snprintf(out, n, "ok mscnt=%lu pos=%ld per=%lu moving=%d", (unsigned long)(v & 1023),
                        (long)s.pos, (unsigned long)tmc_mscnt_per_step(b->mres),
                        s.moving || s2.moving || s.pos != s2.pos);
    }

    /* gstat: read and clear (bit 0 reset, 1 drv_err, 2 uv_cp) */
    if (!strcmp(c, "gstat")) {
        int e = b->ops.tmc_read(b->ops.ctx, TMC_GSTAT, &v);
        if (!e)
            e = wr(b, TMC_GSTAT, v & 7);
        if (e)
            return snprintf(out, n, "err uart %d", e);
        return snprintf(out, n, "ok gstat=0x%lx reset=%d", (unsigned long)(v & 7), (int)(v & 1));
    }

    if (!strcmp(c, "drv")) {
        int e = b->ops.tmc_read(b->ops.ctx, TMC_DRV_STATUS, &v);
        if (e)
            return snprintf(out, n, "err uart %d", e);
        return snprintf(out, n, "ok drv=0x%08lx otpw=%d ot=%d stst=%d", (unsigned long)v,
                        (int)(v & 1), (int)((v >> 1) & 1), (int)(v >> 31));
    }

    return snprintf(out, n, "err unknown: %s", c);
}
