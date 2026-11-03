/* pitch.h -- one string's pitch and note events, from its optical signal, in plain C.

The Pi's detector (control-architecture split: the Pi does pitch detection; the motor board
never sees audio). One `pitch_t` per string, fed the string's demodulated signal at 48 kHz
(the bench package's optical.py: SUM or DIFF of its two photodiodes) in blocks of any length.

    pitch_t p;
    pitch_init(&p, 48000.0f);
    n = pitch_push(&p, block, len, frames, max_frames);   -> frames every 2 ms

What it reports, and why each part is the way it is (docs/design-validation.md, C6 bounds):
  * PITCH by YIN (de Cheveigne and Kawahara 2002) at 12 kHz, lags for 60 to 1000 Hz. The
    difference function is kept up to date sample by sample, so a frame costs its lag count,
    not lag count x window. Its first dip under a threshold is taken, which is what keeps
    a loud 2nd harmonic (string 1's sensor A, bench 2026-11-02) from reading an octave up.
  * NOTE-ON by the ENVELOPE, not by pitch: a pluck is a fast rise of the amplitude, a bar
    slide moves pitch with no rise. The envelope is a peak follower that holds over a
    period of C2, so a low note's own cycles do not look like rises; a note-on is it
    doubling against itself 5 ms earlier. A RE-PLUCK of a ringing string need not raise
    the amplitude at all, so once the pitch is steady a second test runs: a ringing (or
    sliding) string repeats itself one period later, and a pick breaks that. Note-on when
    the 2 ms residual of x[n] - x[n - period] reaches a fraction of the note's own power
    and the power has not fallen over that period (a damp breaks the period too).
  * A frame's `steady` counts the frames its pitch has held within 3 %. Commit a note's
    pitch at steady >= 2: the window straddles a re-pluck for its first few ms. A re-pluck while the string still rings is a note-on;
    a slide is not. Note-off is the envelope falling under a fraction of its peak, or to
    the floor.
  * The window is 21.3 ms whatever the note: 1.4 periods of C2, 2.8 of C3. Every instance
    must run at the same `fs` (the filters' coefficients are shared).
*/
#ifndef PITCH_H
#define PITCH_H

#include <stdint.h>

#define PITCH_DECIM     4                       /* 48 kHz in, 12 kHz analysed */
#define PITCH_TAU_MAX   200                     /* 12000 / 200 = 60 Hz, under C2 65.4 */
#define PITCH_TAU_MIN   12                      /* 1000 Hz */
#define PITCH_WIN       256                     /* samples summed per lag, 21.3 ms */
#define PITCH_HOP       24                      /* a frame every 2 ms */
#define PITCH_LOOK      64                      /* 5.3 ms at 12 kHz, power of 2 */
#define PITCH_RING      512                     /* > PITCH_WIN + PITCH_TAU_MAX, power of 2 */

enum { PITCH_NONE = 0, PITCH_ON = 1, PITCH_OFF = 2 };

typedef struct {
    double t;           /* seconds since pitch_init, at the frame's newest sample */
    float hz;           /* 0 when unvoiced */
    float clarity;      /* 1 - YIN's normalised dip: 1 is a perfect period */
    float env;          /* amplitude, input units */
    int event;          /* PITCH_ON / PITCH_OFF at this frame */
    int steady;         /* frames before this one that agreed with it, within 3 % */
} pitch_frame_t;

typedef struct {
    float fs;
    /* decimating low-pass (two biquads at 2.5 kHz) and a 30 Hz high-pass */
    float lp[2][4], hp[4];
    int phase;
    /* analysis ring at 12 kHz and the running difference sums */
    float x[PITCH_RING];
    uint32_t n;                         /* samples written to x */
    double d[PITCH_TAU_MAX + 1];        /* sum over the window of (x[t] - x[t - tau])^2 */
    /* envelope: a peak follower, its own past (PITCH_LOOK samples back), the note's
       peak and the floor */
    float env, past[PITCH_LOOK], peak, floor_;
    int on, hold;
    float last_hz, resid, pnow, pago;
    int steady;                         /* frames in a row the pitch has held */
    double t;
} pitch_t;

void pitch_init(pitch_t *p, float fs);
/* Feed `len` samples; writes up to `max` frames, returns how many. */
int pitch_push(pitch_t *p, const float *in, int len, pitch_frame_t *out, int max);

#endif
