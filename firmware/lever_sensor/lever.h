#ifndef LEVER_H
#define LEVER_H
/* The lever board's logic, with no hardware in it: filtering, calibration, the CAN frames in and
 * out. main.c feeds it angles and the clock and moves its frames; the Pi's simulator compiles
 * this same file natively (bench/publicbench/levers.py, SimLever), so the bench decodes frames
 * the real code made. bench/publicbench/levers.py reads the numbers below from this file.
 *
 * BUS B, 11-bit ids unless marked. A board knows its lever by its SLOT (0-15; 11 used, the order
 * the Pi's map gives them), stored in flash with its calibration. A board with no slot sends
 * only HELLO, so eleven fresh boards never share an id.
 *
 *   0x100+slot  POS    board -> Pi  pos u16 LE (0 rest .. 32767 full, 0xFFFF uncalibrated),
 *                                   status u8 (LV_*), seq u8
 *                                   on a change of DEADBAND, at most every TX_MIN_US; every
 *                                   TX_IDLE_US regardless
 *   0x200+slot  DIAG   board -> Pi  raw u16 (14-bit angle, filtered), rest u16, full u16,
 *                                   field u8 (MA730 MGH 0x80 / MGL 0x40), version u8; every DIAG_US
 *   0x300+slot  CMD    Pi -> board  op u8 then arguments (LC_*)
 *   0x380+slot  REPLY  board -> Pi  op u8, ok u8
 *   0x7F1       ALL    Pi -> every  'I': every board sends HELLO; 'S' uid u32 LE, slot u8: the
 *                                   board with that uid takes the slot and stores it;
 *                                   'H': HOLD THE CHAIN -- every board cuts the next board's 5 V
 *                                   and keeps it off until its own CMD 'N' (a board still in its
 *                                   NEXT_AFTER_US start window stays held too). A next board
 *                                   that an 'N' 1 let up STAYS up, so the Pi can say 'H' again
 *                                   the moment each new board appears: that board was dark at
 *                                   the first 'H', and would otherwise power the one after it
 *                                   NEXT_AFTER_US later, before its own 'N';
 *                                   'U' ms u16 LE, slot u8: RELEASE THE PAIR for a flash over USB
 *                                   (docs/lever-usb-flash.md): every board turns its transceiver
 *                                   off, lets go of CAN_H / CAN_L and waits, silent, for the arm's
 *                                   power cycle; the board in `slot` also cuts the next board's
 *                                   5 V and gives it back ms later, so THAT board -- and only it,
 *                                   the ones after it staying dark -- starts on a pair the Pi holds
 *                                   as USB and comes up in WCH's ROM loader (BOOT0 is set by the
 *                                   bus, whatever firmware it has). slot 0xFF: nobody cycles
 *                                   (the first board, which motor_ctrl powers itself).
 *
 * FINDING A BOARD IN THE CHAIN. Each board powers the next (J2's 5 V), NEXT_AFTER_US after it
 * starts. So the chain's order is learned by holding it ('H') and letting it up one board at a
 * time ('N' 1 to each in turn): the HELLO that follows a board's 'N' is the board after it. A
 * board that sends nothing after its predecessor's 'N' is the broken one, and its predecessor's
 * slot is the 'U' that reflashes it. The Pi keeps the order it learned (levers chain).
 *   29-bit 0x1E000000 | uid & 0xFFFFFF  HELLO  board -> Pi
 *                                   uid u32 LE, slot u8 (0xFF none), version u8, mode u8
 *                                   (0 application, 1 loader), status u8. At start, on 'I', and
 *                                   every HELLO_US while the board has no slot. The uid in the id
 *                                   keeps two boards' HELLOs from ever arbitrating as one frame.
 *
 * Load at 500 kbit/s: a POS frame is about 90 bits, so a lever moving flat out is 45 kbit/s
 * (9 %), and all eleven at once 100 %, which a pedal-and-knee player does not do; four at once
 * is 36 %. Idle, eleven boards' heartbeats and DIAGs come to about 7 %. */
#include <stdint.h>

#define LEVER_VERSION 1

#define ID_POS     0x100u
#define ID_DIAG    0x200u
#define ID_CMD     0x300u
#define ID_REPLY   0x380u
#define ID_ALL     0x7F1u
#define ID_HELLO   0x1E000000u              /* 29-bit, | (uid & 0xFFFFFF) */

#define SLOT_NONE  0xFFu
#define SLOTS      16u
#define POS_FULL   32767u
#define POS_NONE   0xFFFFu

#define SAMPLE_US  1000u                    /* one angle read */
#define FIELD_US   10000u                   /* one MA730 field-flags read */
#define TX_MIN_US  2000u
#define TX_IDLE_US 50000u
#define DIAG_US    100000u
#define HELLO_US   1000000u
#define DEADBAND   8u                       /* POS units: 0.025 % of travel */
#define MIN_SPAN   200u                     /* counts (4.4 deg): less is no calibration */

/* status bits */
#define LV_MGL     0x01u                    /* field weak: magnet missing, far or cracked */
#define LV_MGH     0x02u                    /* field strong: too close, or the wrong magnet */
#define LV_UNCAL   0x04u                    /* no usable rest / full */
#define LV_UNSAVED 0x08u                    /* calibration changed, not in flash yet */
#define LV_OUTSIDE 0x10u                    /* past an end stop by more than 1/32 of travel */

/* CMD ops */
#define LC_REST    'R'                      /* rest = this angle */
#define LC_FULL    'F'                      /* full = this angle */
#define LC_CAL     'K'                      /* rest u16, full u16: set both */
#define LC_SAVE    'W'                      /* calibration and slot to flash */
#define LC_SLOT    'S'                      /* slot u8: move to another slot (then W) */
#define LC_THRESH  'T'                      /* mglt u8, mght u8: MA730 register 6 (non-volatile) */
#define LC_HELLO   'I'
#define LC_LOADER  'B'                      /* restart in the CAN loader, if there is one */
#define LC_RELEASE 'U'                      /* ALL only: ms u16, slot u8 (see above) */
#define LC_HOLD    'H'                      /* ALL only: next boards' power off until 'N' */
#define LC_NEXT    'N'                      /* on u8: the next board's 5 V on (1) / off (0) */
#define NEXT_AFTER_US 100000u               /* a board powers the next this long after start */

typedef struct {
    uint32_t magic;                         /* CFG_MAGIC */
    uint8_t slot, mglt, mght, spare;        /* mglt / mght 0xFF: leave the part's own */
    uint16_t rest, full;                    /* 14-bit angles */
    uint32_t crc;                           /* lever_crc32 of everything before it */
} lever_cfg_t;
#define CFG_MAGIC  0x4C565231u              /* "LVR1" */

typedef struct {
    uint32_t id;
    uint8_t ext, len, d[8];
} lever_frame_t;

typedef struct {
    lever_cfg_t cfg;
    uint32_t uid;
    uint8_t mode;                           /* what HELLO says: 0 application, 1 loader */
    int32_t acc[3];                         /* the last three angles, unwrapped, counts */
    uint8_t n;                              /* samples so far, to 3 */
    uint16_t prev_raw;
    int32_t filt;                           /* filtered angle, 1/16 counts, unwrapped */
    uint8_t field, seq, unsaved;
    uint16_t sent_pos;
    uint8_t sent_status;
    uint32_t t_pos, t_diag, t_hello;
    uint8_t hello_now, reply_n;
    lever_frame_t reply;
    /* for main.c to act on, then clear */
    uint8_t want_save, want_loader, want_thresh;
    uint16_t want_release;                  /* ms (1 or more): LC_RELEASE heard */
    uint8_t release_cycle;                  /* ...and this board is the one that cycles */
    uint8_t want_next;                      /* 0 nothing, 1 next board on, 2 off (LC_NEXT) */
    uint8_t held;                           /* LC_HOLD heard: no automatic power-up */
    uint8_t next_by_cmd;                    /* the next board is on by an 'N' 1, not by itself */
} lever_t;

uint32_t lever_crc32(const void *p, uint32_t n);
int lever_cfg_ok(const lever_cfg_t *c);
void lever_cfg_seal(lever_cfg_t *c);

/* stored: the flash copy, or 0. now_us: the clock, so the first HELLO goes at once. */
void lever_init(lever_t *l, const lever_cfg_t *stored, uint32_t uid, uint32_t now_us);
void lever_sample(lever_t *l, uint16_t raw14);      /* every SAMPLE_US */
void lever_field(lever_t *l, uint8_t mgh_mgl);      /* MA730 register 27, every FIELD_US */
uint16_t lever_raw(const lever_t *l);               /* the filtered 14-bit angle */
uint16_t lever_pos(const lever_t *l);               /* POS_NONE uncalibrated */
uint8_t lever_status(const lever_t *l);
/* the next frame to send, if one is due: 1 and *out filled, else 0. Call while the controller
 * has a free mailbox. */
int lever_poll(lever_t *l, uint32_t now_us, lever_frame_t *out);
void lever_rx(lever_t *l, const lever_frame_t *in);  /* a frame the filter let through */
#endif
