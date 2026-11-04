/* Bus B's two arms on motor_ctrl R2, and J4's pair: what lever flashing switches
 * (docs/lever-usb-flash.md, elec/motor_ctrl.py _arm_switches / _link_select).
 *
 *   arm 0  the pedals, J2: U6 its 5 V (EN on PC12), U9 its pair (S on PD9)
 *   arm 1  the levers, J6: U11 its 5 V (EN on PD2), U10 its pair (S on PD8)
 *   lane   J4's pair: U7, the link (PA2 low), or the arms' flash lane (PA2 high)
 *
 * Pure logic: main.c applies the state to the pins, and the simulator runs this file as it is
 * (bench/publicbench/simarms.py).
 *
 * A FLASH WINDOW hands one arm's pair to the Pi's USB for ms milliseconds. J4 goes with it, so
 * the link to the Pi is down for the whole window and nothing can end it early: it ends by
 * itself. Then J4 is the link again, both arms are CAN, and BOTH arms are power-cycled -- an
 * ALL 'U' (lever.h LC_RELEASE) parks every lever and pedal board on the bus, not only the ones
 * on the arm being flashed, and only a power cycle brings them back.
 *   ARM_LEAD_US  between the command and the switch, so the OK reply leaves on the link first
 *   cycle = 1    the arm is also powered off at the start and back on ARM_OFF_US later, onto
 *                the USB pair: the first board of the arm comes up in WCH's ROM loader (lever.h
 *                slot 0xFF: no board before it to do the cycling)
 */
#ifndef ARMS_H
#define ARMS_H
#include <stdint.h>

#define ARMS 2
#define ARM_LEAD_US    20000u           /* command -> switch: the reply goes first */
#define ARM_OFF_US     200000u          /* how long an arm is held dark in a power cycle */
#define ARM_WINDOW_MAX 60000u           /* ms: the longest flash window taken */

typedef struct {
    uint8_t power[ARMS];                /* 1: the arm's 5 V is on */
    uint8_t usb[ARMS];                  /* 1: the arm's pair is on the flash lane */
    uint8_t lane;                       /* 1: J4 is the flash lane (the link is down) */
    /* pending, all in now_us() terms (wrapping 32-bit) */
    uint8_t start, cycle, arm, stop;
    uint32_t start_at, stop_at;
    uint8_t on_pending[ARMS];
    uint32_t on_at[ARMS];
} arms_t;

void arms_init(arms_t *a);                       /* both arms on and CAN, J4 the link */
/* 0 off, 1 on, 2 cycle (off, on ARM_OFF_US later). 0 = refused (bad arm, or a window open). */
int arms_power(arms_t *a, unsigned arm, unsigned what, uint32_t now);
/* a flash window on `arm` for ms; 0 = refused (bad arm, ms 0 or over ARM_WINDOW_MAX, one open) */
int arms_flash(arms_t *a, unsigned arm, uint32_t ms, unsigned cycle, uint32_t now);
void arms_poll(arms_t *a, uint32_t now);         /* run the pending steps that are due */
int arms_busy(const arms_t *a);                  /* a window is open or about to be */

#endif
