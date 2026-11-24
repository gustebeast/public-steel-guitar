/* The bench firmware's command line: one text line in, one line out ("ok ..." or "err ..."),
 * over the QT Py's USB-CDC. The hardware is behind bench_ops_t, so bench/tests/test_qtpy_bench.py
 * runs this file natively against a pretend driver. The commands are listed in README.md. */
#ifndef BENCH_H
#define BENCH_H

#include <stdint.h>
#include "axis.h"

#define BENCH_VERSION "qtpy_bench 1"

typedef struct {
    void (*enable)(void *ctx, int on);                       /* ENN low (on) or high (off) */
    int  (*tmc_read)(void *ctx, uint8_t reg, uint32_t *v);   /* 0 ok, <0 a UART/CRC fault */
    int  (*tmc_write)(void *ctx, uint8_t reg, uint32_t v);
    void (*step_start)(void *ctx, int dir, uint32_t first);  /* set DIR, first edge in `first` ticks */
    void (*step_stop)(void *ctx);                            /* no more edges */
    void (*lock)(void *ctx);                                 /* step ISR off / back on, so the */
    void (*unlock)(void *ctx);                               /* axis is read in one piece */
    void *ctx;
} bench_ops_t;

typedef struct {
    axis_t      ax;
    bench_ops_t ops;
    int         mres;      /* CHOPCONF MRES code: 6 = 4 steps per full step */
    int         enabled;
    uint32_t    rsense;    /* mOhm: the SilentStepStick's 110 */
    uint32_t    irun, ihold, iholddelay;   /* IHOLD_IRUN scales, 0..31 */
} bench_t;

void     bench_init(bench_t *b, const bench_ops_t *ops, uint32_t rsense_mohm);
/* runs one command line; writes the reply (no newline) into out, returns its length */
int      bench_line(bench_t *b, const char *line, char *out, int outlen);
/* from the step timer's ISR, after each edge: ticks to the next edge, or 0 to stop */
uint32_t bench_step_isr(bench_t *b);

#endif
