/* pitch.c -- see pitch.h for what this is and why. */
#include "pitch.h"

#include <math.h>
#include <string.h>

#define YIN_THRESH      0.15f   /* first dip under this is the period */
#define YIN_ACCEPT      0.35f   /* a frame whose best dip is over this is unvoiced */
#define ENV_REL_MS      30.0f   /* peak follower's release: two periods of C2 */
#define ON_RATIO        2.0f    /* the envelope doubled in PITCH_LOOK: a pluck */
#define ON_FLOOR        6.0f    /* ...and stands this many times over the floor */
#define FLOOR_MS        200.0f  /* the floor follows the quiet this slowly */
#define WARMUP_MS       50.0f   /* no note-on before the floor has been seen */
#define OFF_FRACTION    0.04f   /* note-off under this much of the note's peak (-28 dB) */
#define HOLD_MS         30.0f   /* no second note-on within this of the first */
#define RESID_MS        2.0f    /* the period residual's averaging */
#define RESID_ON        0.25f   /* residual power over the note's (env^2 / 2): a re-pluck */
#define KEEP_POWER      0.8f    /* ...and power a period on at least this much of it */
#define STEADY_FRAMES   3       /* the period test needs the pitch held this long */

/* RBJ biquad low-pass, Q = 1/sqrt(2); b0 b1 b2 a1 a2 normalised */
static void lowpass(float *c, float fs, float f)
{
    float w = 2.0f * (float)M_PI * f / fs, al = sinf(w) / (2.0f * 0.70710678f), cw = cosf(w);
    float a0 = 1.0f + al;
    c[0] = (1.0f - cw) / 2.0f / a0;
    c[1] = (1.0f - cw) / a0;
    c[2] = c[0];
    c[3] = -2.0f * cw / a0;
    c[4] = (1.0f - al) / a0;
}

static void highpass(float *c, float fs, float f)
{
    float w = 2.0f * (float)M_PI * f / fs, al = sinf(w) / (2.0f * 0.70710678f), cw = cosf(w);
    float a0 = 1.0f + al;
    c[0] = (1.0f + cw) / 2.0f / a0;
    c[1] = -(1.0f + cw) / a0;
    c[2] = c[0];
    c[3] = -2.0f * cw / a0;
    c[4] = (1.0f - al) / a0;
}

static float LP[5], HP[5];

static float biquad(const float *c, float *s, float x)       /* transposed direct form II */
{
    float y = c[0] * x + s[0];
    s[0] = c[1] * x - c[3] * y + s[1];
    s[1] = c[2] * x - c[4] * y;
    return y;
}

void pitch_init(pitch_t *p, float fs)
{
    memset(p, 0, sizeof *p);
    p->fs = fs;
    lowpass(LP, fs, 2500.0f);
    highpass(HP, fs / PITCH_DECIM, 30.0f);
    p->floor_ = 1e-3f;
}

#define X(i) (p->x[(i) & (PITCH_RING - 1)])

/* one 12 kHz sample: slide every lag's difference sum along by one */
static void slide(pitch_t *p, float v)
{
    uint32_t n = p->n;
    X(n) = v;
    p->n = n + 1;
    if (n < PITCH_WIN + PITCH_TAU_MAX)
        return;                                 /* sums start once the ring is full */
    for (int tau = 1; tau <= PITCH_TAU_MAX; tau++) {
        float in = X(n) - X(n - tau), out = X(n - PITCH_WIN) - X(n - PITCH_WIN - tau);
        p->d[tau] += (double)in * in - (double)out * out;
    }
}

/* the window's first fill: sums from scratch (also every so often, against round-off) */
static void resum(pitch_t *p)
{
    uint32_t end = p->n - 1;
    for (int tau = 1; tau <= PITCH_TAU_MAX; tau++) {
        double s = 0.0;
        for (int j = 0; j < PITCH_WIN; j++) {
            float e = X(end - j) - X(end - j - tau);
            s += (double)e * e;
        }
        p->d[tau] = s;
    }
}

/* YIN's cumulative-mean-normalised difference, first dip under the threshold */
static float yin(const pitch_t *p, float *clarity)
{
    float dn[PITCH_TAU_MAX + 1];
    double run = 0.0;
    dn[0] = 1.0f;
    for (int tau = 1; tau <= PITCH_TAU_MAX; tau++) {
        run += p->d[tau];
        dn[tau] = run > 0.0 ? (float)(p->d[tau] * tau / run) : 1.0f;
    }
    int best = -1;
    for (int tau = PITCH_TAU_MIN; tau < PITCH_TAU_MAX; tau++) {
        if (dn[tau] < YIN_THRESH) {
            while (tau + 1 < PITCH_TAU_MAX && dn[tau + 1] < dn[tau])
                tau++;
            best = tau;
            break;
        }
    }
    if (best < 0) {                             /* no dip under it: the deepest, if good enough */
        best = PITCH_TAU_MIN;
        for (int tau = PITCH_TAU_MIN; tau < PITCH_TAU_MAX; tau++)
            if (dn[tau] < dn[best])
                best = tau;
    }
    *clarity = 1.0f - dn[best];
    if (dn[best] > YIN_ACCEPT || best <= PITCH_TAU_MIN || best >= PITCH_TAU_MAX - 1)
        return 0.0f;
    float a = dn[best - 1], b = dn[best], c = dn[best + 1];  /* parabola through the dip */
    float den = a - 2.0f * b + c;
    float t = best + (den > 0.0f ? 0.5f * (a - c) / den : 0.0f);
    return (p->fs / PITCH_DECIM) / t;
}

int pitch_push(pitch_t *p, const float *in, int len, pitch_frame_t *out, int max)
{
    const float fs2 = p->fs / PITCH_DECIM;
    const float rel = expf(-1000.0f / (ENV_REL_MS * fs2));
    const float kfl = 1.0f - expf(-1000.0f / (FLOOR_MS * fs2));
    const uint32_t warm = (uint32_t)(WARMUP_MS * fs2 / 1000.0f);
    const float kr = 1.0f - expf(-1000.0f / (RESID_MS * fs2));
    int nout = 0;
    for (int i = 0; i < len; i++) {
        float y = biquad(LP, p->lp[0], in[i]);
        y = biquad(LP, p->lp[1], y);
        if (++p->phase < PITCH_DECIM)
            continue;
        p->phase = 0;
        float v = biquad(HP, p->hp, y);
        slide(p, v);
        p->t = (double)p->n / fs2;

        /* envelope */
        float r = fabsf(v);
        p->env = r > p->env * rel ? r : p->env * rel;
        float before = p->past[p->n & (PITCH_LOOK - 1)];
        p->past[p->n & (PITCH_LOOK - 1)] = p->env;
        int event = PITCH_NONE;
        if (p->hold > 0)
            p->hold--;
        int period_break = 0;
        if (p->on && p->steady >= STEADY_FRAMES) {
            float T = fs2 / p->last_hz, fr = T - floorf(T);
            uint32_t k = p->n - 1 - (uint32_t)floorf(T);
            float ago = (1.0f - fr) * X(k) + fr * X(k - 1), e = v - ago;
            p->resid += kr * (e * e - p->resid);
            p->pnow += kr * (v * v - p->pnow);
            p->pago += kr * (ago * ago - p->pago);
            period_break = p->resid > RESID_ON * 0.5f * p->env * p->env
                           && p->pnow > KEEP_POWER * p->pago;
        } else {
            p->resid = p->pnow = p->pago = 0.0f;
        }
        if (p->n < warm) {
            p->floor_ = p->n ? p->floor_ + (p->env - p->floor_) / (float)p->n : p->env;
        } else if (((p->env > ON_RATIO * before && p->env > ON_FLOOR * p->floor_) || period_break)
                   && p->hold == 0) {
            event = PITCH_ON;
            p->on = 1;
            p->peak = p->env;
            p->steady = 0;
            p->hold = (int)(HOLD_MS * fs2 / 1000.0f);
        } else if (p->on) {
            if (p->env > p->peak)
                p->peak = p->env;
            if (p->env < OFF_FRACTION * p->peak || p->env < 2.0f * p->floor_) {
                event = PITCH_OFF;
                p->on = 0;
            }
        } else {
            p->floor_ += kfl * (p->env - p->floor_);
        }

        if (p->n == PITCH_WIN + PITCH_TAU_MAX + 1 || (p->n & 0x3FFF) == 0)
            resum(p);
        if ((p->n % PITCH_HOP) && event == PITCH_NONE)
            continue;
        if (nout >= max)
            continue;
        pitch_frame_t *f = &out[nout++];
        f->t = p->t;
        f->env = p->env;
        f->event = event;
        f->clarity = 0.0f;
        f->hz = 0.0f;
        if (p->n > PITCH_WIN + PITCH_TAU_MAX && p->on)
            f->hz = yin(p, &f->clarity);
        if (event == PITCH_NONE)
            p->steady = f->hz > 0.0f && fabsf(f->hz - p->last_hz) < 0.03f * f->hz ? p->steady + 1 : 0;
        if (f->hz > 0.0f || event != PITCH_NONE)
            p->last_hz = f->hz;
        f->steady = p->steady;
    }
    return nout;
}
