/* One stepper axis's move planner: a trapezoid of step intervals, computed one step at a time
 * with integers only (D. Austin's recurrence, as in Atmel AVR446), so the same code can run ten
 * axes on a CH32V203 with no FPU. No hardware here: bench/tests/test_qtpy_bench.py compiles it
 * natively.
 *
 * Units: positions in driver steps at the current MRES; speeds in steps/s; accelerations in
 * steps/s^2; intervals in ticks of AXIS_TICK_HZ.
 */
#ifndef AXIS_H
#define AXIS_H

#include <stdint.h>

#define AXIS_TICK_HZ 8000000u   /* the step timer's clock */
#define AXIS_CMAX    65535u     /* the longest interval a 16-bit compare can hold */
#define AXIS_CMIN    40u        /* 5 us: the shortest interval the step ISR is given */

typedef struct {
    int32_t  pos;        /* steps sent so far, signed */
    int32_t  target;
    int8_t   dir;        /* +1 or -1 for the move in progress */
    uint8_t  moving;
    uint32_t total;      /* steps in this move */
    uint32_t done;
    uint32_t acc_end;    /* steps [1, acc_end) accelerate */
    uint32_t dec_start;  /* steps [dec_start, total) decelerate */
    uint32_t c;          /* the current interval, ticks << 8 */
    uint32_t cmin;       /* the cruise interval, ticks << 8 */
} axis_t;

/* Plans a move to `target`. Returns the ticks before the first step, or 0 when there is nothing
 * to do (already there, or a zero speed or acceleration). dir is set either way. */
uint32_t axis_start(axis_t *a, int32_t target, uint32_t vmax, uint32_t acc);

/* Called once per step, just after the step edge went out: counts it, and returns the ticks to
 * the next step, or 0 when the move is complete (moving is then 0 and pos == target). */
uint32_t axis_next(axis_t *a);

/* Stops at once: the target becomes wherever the steps sent so far put it. */
void axis_halt(axis_t *a);

#endif
