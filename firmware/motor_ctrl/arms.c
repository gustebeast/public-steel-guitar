/* Bus B's arms and J4's pair (arms.h). */
#include "arms.h"

static int due(uint32_t now, uint32_t at) { return (int32_t)(now - at) >= 0; }

static void dark(arms_t *a, unsigned arm, uint32_t now)
{
    a->power[arm] = 0;
    a->on_pending[arm] = 1;
    a->on_at[arm] = now + ARM_OFF_US;
}

void arms_init(arms_t *a)
{
    for (unsigned i = 0; i < ARMS; i++) {
        a->power[i] = 1; a->usb[i] = 0; a->on_pending[i] = 0; a->on_at[i] = 0;
    }
    a->lane = 0;
    a->start = a->cycle = a->arm = a->stop = 0;
    a->start_at = a->stop_at = 0;
}

int arms_busy(const arms_t *a) { return a->start || a->stop; }

int arms_power(arms_t *a, unsigned arm, unsigned what, uint32_t now)
{
    if (arm >= ARMS || what > 2 || arms_busy(a)) return 0;
    if (what == 2) dark(a, arm, now);
    else { a->power[arm] = (uint8_t)what; a->on_pending[arm] = 0; }
    return 1;
}

int arms_flash(arms_t *a, unsigned arm, uint32_t ms, unsigned cycle, uint32_t now)
{
    if (arm >= ARMS || ms == 0 || ms > ARM_WINDOW_MAX || arms_busy(a)) return 0;
    a->start = 1; a->cycle = (uint8_t)(cycle != 0); a->arm = (uint8_t)arm;
    a->start_at = now + ARM_LEAD_US;
    a->stop_at = a->start_at + ms * 1000u;
    return 1;
}

void arms_poll(arms_t *a, uint32_t now)
{
    if (a->start && due(now, a->start_at)) {
        a->start = 0;
        if (a->cycle) dark(a, a->arm, now);
        a->usb[a->arm] = 1;
        a->lane = 1;
        a->stop = 1;
    }
    if (a->stop && due(now, a->stop_at)) {
        a->stop = 0;
        a->lane = 0;
        for (unsigned i = 0; i < ARMS; i++) {
            a->usb[i] = 0;
            dark(a, i, now);
        }
    }
    for (unsigned i = 0; i < ARMS; i++)
        if (a->on_pending[i] && due(now, a->on_at[i])) { a->on_pending[i] = 0; a->power[i] = 1; }
}
