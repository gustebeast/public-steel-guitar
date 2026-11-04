#ifndef PLAY_H
#define PLAY_H
/* The instrument's one real-time job (docs/control-path.md): lever and pedal positions in from
 * bus B, motor targets out on bus A, through a table the Pi wrote. Pure C, no hardware, no
 * library calls: main.c moves the frames and keeps the clock, and the bench compiles this same
 * file natively (bench/publicbench/simplay.py) so its tests run the code that goes on the board.
 *
 * WHERE THE COPEDENT LIVES. The Pi owns it as music (bench/publicbench/copedent.json: per
 * control, per string, semitones at full travel) and owns every string's calibration (motor
 * counts against pitch, measured while tuning). It compiles both into play_table_t and writes
 * that down. This board only multiplies and looks up, so it plays with the Pi absent.
 *
 * Per string, every tick that something moved:
 *   up    = the largest  pos_c * cents[c][s] over the controls that raise it (0 if none)
 *   down  = the smallest pos_c * cents[c][s] over the controls that lower it (0 if none)
 *   pitch = up + down cents above open
 * Raises do not add to raises: two pedals that both raise a string to D leave it at D, as two
 * pulls on one changer finger do. A raise and a lower do add, as the two fingers of a changer do.
 * pitch -> counts through the string's curve (piecewise linear, knots every KNOT_CENTS from
 * KNOT_LO), relative to the string's BASE: where its motor stood at open pitch. The curve, not
 * a factor, because tension goes as pitch squared and every string's belt and frame stretch is
 * its own.
 *
 * BASE. After a power cycle a motor's turn count is gone, but the screw holds the carriage where
 * it was: at open pitch, if every control was at rest when the power went. So at start each
 * motor is asked where it is (0x31) and that reading is its open pitch; then it is told to answer
 * a move once, when it starts, and not again when it arrives (0x8C 01 00: manual V1.0.9 5.2.12,
 * a third less wire time on bus A per move); then it is enabled (0xF3). The Pi re-bases
 * (play_rebase) after it tunes. A string is not driven until based.
 *
 * Frames to the motors are SERVO42D frames (bench/publicbench/servo.py): F5 absolute moves, at
 * most one per motor every min_us; the newest target wins, so a move's first frame goes at once
 * and only the updates of a continuing move wait. Replies to moves are ignored. */
#include <stdint.h>

#define PLAY_STRINGS    10u
#define PLAY_SLOTS      16u                 /* lever.h SLOTS */
#define PLAY_KNOTS      21u
#define KNOT_LO         (-400)              /* cents: the curve's first knot */
#define KNOT_CENTS      50                  /* ...and the step between knots: -4 .. +6 semitones */
#define PLAY_MAGIC      0x59414C50u         /* "PLAY" */
#define PLAY_VERSION    1u

#define PLAY_POS_ID     0x100u              /* lever.h ID_POS */
#define PLAY_POS_FULL   32767u
#define PLAY_LOST_US    150000u             /* 3 x lever.h TX_IDLE_US: a silent lever is at rest */
#define PLAY_ASK_US     100000u             /* asking an unbased motor where it is */
#define PLAY_DEADBAND   4                   /* counts: ~0.1 cent on string 1 */

#define SV_READ_ENC     0x31u
#define SV_ENABLE       0xF3u
#define SV_RESPOND      0x8Cu               /* respond u8, active u8 */
#define SV_MOVE_ABS     0xF5u

/* The table, as it sits in flash and on the wire from the Pi: little-endian, no padding
 * (every field is aligned by position). crc is zlib's crc32 of everything before it. */
typedef struct {
    uint32_t magic;
    uint16_t version;
    uint16_t rpm;                           /* F5 speed, 0..3000 */
    uint8_t  acc;                           /* F5 acc: 0 = no ramp (fastest, motor-step-results) */
    uint8_t  spare[3];
    uint32_t min_us;                        /* per motor, between two F5 frames */
    uint8_t  motor[PLAY_STRINGS];           /* string N (index N-1): its motor's CAN id, 0 none */
    uint8_t  spare2[2];
    int16_t  cents[PLAY_SLOTS][PLAY_STRINGS];   /* at full travel, signed */
    int32_t  curve[PLAY_STRINGS][PLAY_KNOTS];   /* counts from base at each knot; 0 at 0 cents */
    uint32_t crc;
} play_table_t;

enum { PS_UNBASED, PS_QUIET, PS_ENABLE, PS_DRIVE };  /* a string's state */

typedef struct { uint32_t id; uint8_t ext, len, d[8]; } play_frame_t;   /* = lever_frame_t */

typedef struct {
    play_table_t t;
    uint8_t  ok;                            /* t is checked */
    uint8_t  on;                            /* drive the motors */
    uint16_t pos[PLAY_SLOTS];               /* 0..POS_FULL */
    uint32_t heard[PLAY_SLOTS];             /* now_us of the last POS */
    uint8_t  state[PLAY_STRINGS];           /* PS_* */
    int32_t  base[PLAY_STRINGS];
    int32_t  target[PLAY_STRINGS];          /* from base: what it should be */
    int32_t  sent[PLAY_STRINGS];            /* ...and what the motor was last told */
    uint8_t  told[PLAY_STRINGS];            /* sent is valid */
    uint32_t last[PLAY_STRINGS];            /* now_us of the last frame to that motor */
    uint8_t  dirty;                         /* a position changed: recompute targets */
    uint8_t  rr;                            /* round robin over the strings */
    uint32_t moves;                         /* F5 frames sent, for the bench */
} play_t;

uint32_t play_crc32(const void *d, uint32_t n);         /* zlib's */
int  play_table_ok(const play_table_t *t);
void play_init(play_t *p, const play_table_t *t);       /* t NULL or bad: nothing is driven */
int  play_load(play_t *p, const play_table_t *t);       /* a new table; the bases are kept */
void play_rx(play_t *p, uint8_t bus, const play_frame_t *f, uint32_t now_us);  /* 0 A, 1 B */
int  play_poll(play_t *p, uint32_t now_us, play_frame_t *out);  /* 1: send *out on bus A */
void play_rebase(play_t *p);                            /* every motor's position = open pitch */
int32_t play_cents(const play_t *p, uint8_t string_index);     /* the pitch it is driving to */
int32_t play_counts(const play_table_t *t, uint8_t string_index, int32_t cents);
#endif
