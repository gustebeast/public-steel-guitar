/* TMC2209 single-wire UART: datagrams, CRC and the register values the bench uses. Datasheet
 * Rev 1.03 section 4 (p15-19) for the framing and CRC, section 5 for the registers. No hardware
 * here: bench/tests/test_qtpy_bench.py compiles it natively. */
#ifndef TMC_H
#define TMC_H

#include <stdint.h>

#define TMC_SYNC        0x05
#define TMC_REPLY_ADDR  0xFF    /* a read reply's address byte (p17) */

#define TMC_GCONF       0x00
#define TMC_GSTAT       0x01
#define TMC_IFCNT       0x02
#define TMC_IHOLD_IRUN  0x10
#define TMC_TPOWERDOWN  0x11
#define TMC_MSCNT       0x6A
#define TMC_CHOPCONF    0x6C
#define TMC_DRV_STATUS  0x6F

/* GCONF: internal current reference (I_scale_analog 0), StealthChop, pdn_disable (needed with
 * the UART), mstep_reg_select (MRES from CHOPCONF), multistep_filt off (dedge needs it off). */
#define TMC_GCONF_BENCH ((1u << 6) | (1u << 7))

/* CHOPCONF's reset default (p30) with MRES and dedge replaced; intpol stays on. */
#define TMC_CHOPCONF_DEFAULT 0x10000053u

uint8_t  tmc_crc(const uint8_t *d, int n);
void     tmc_write_dg(uint8_t out[8], uint8_t addr, uint8_t reg, uint32_t v);
void     tmc_read_dg(uint8_t out[4], uint8_t addr, uint8_t reg);
/* 0 ok, -1 bad sync or address byte, -2 bad CRC, -3 a reply for another register */
int      tmc_parse_reply(const uint8_t in[8], uint8_t reg, uint32_t *v);

/* MRES code 0..8 = 256, 128, ... 2, 1 (full) steps per full step; mres_code(4) == 6 */
int      tmc_mres_code(uint32_t microsteps);
uint32_t tmc_chopconf(int mres_code, int dedge);
/* MSCNT counts 1024 per electrical cycle; one step at this MRES advances it this much */
uint32_t tmc_mscnt_per_step(int mres_code);

/* IHOLD_IRUN's current scale (0..31) for an RMS current in mA, with sense resistors of
 * rsense_mohm and vsense 0 (p50: I = (CS+1)/32 * 0.325 V / (R + 20 mOhm) / sqrt 2), and back */
uint32_t tmc_cs_for_ma(uint32_t ma, uint32_t rsense_mohm);
uint32_t tmc_ma_for_cs(uint32_t cs, uint32_t rsense_mohm);
uint32_t tmc_ihold_irun(uint32_t ihold, uint32_t irun, uint32_t iholddelay);

#endif
