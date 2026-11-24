#include "tmc.h"

/* the datasheet's own routine (p17): CRC-8, polynomial x^8 + x^2 + x + 1, bits LSB first */
uint8_t tmc_crc(const uint8_t *d, int n)
{
    uint8_t crc = 0;
    for (int i = 0; i < n; i++) {
        uint8_t b = d[i];
        for (int j = 0; j < 8; j++) {
            if ((crc >> 7) ^ (b & 1))
                crc = (uint8_t)((crc << 1) ^ 0x07);
            else
                crc = (uint8_t)(crc << 1);
            b >>= 1;
        }
    }
    return crc;
}

void tmc_write_dg(uint8_t out[8], uint8_t addr, uint8_t reg, uint32_t v)
{
    out[0] = TMC_SYNC;
    out[1] = addr;
    out[2] = (uint8_t)(reg | 0x80);
    out[3] = (uint8_t)(v >> 24);
    out[4] = (uint8_t)(v >> 16);
    out[5] = (uint8_t)(v >> 8);
    out[6] = (uint8_t)v;
    out[7] = tmc_crc(out, 7);
}

void tmc_read_dg(uint8_t out[4], uint8_t addr, uint8_t reg)
{
    out[0] = TMC_SYNC;
    out[1] = addr;
    out[2] = (uint8_t)(reg & 0x7F);
    out[3] = tmc_crc(out, 3);
}

int tmc_parse_reply(const uint8_t in[8], uint8_t reg, uint32_t *v)
{
    if ((in[0] & 0x0F) != TMC_SYNC || in[1] != TMC_REPLY_ADDR)
        return -1;
    if (tmc_crc(in, 7) != in[7])
        return -2;
    if ((in[2] & 0x7F) != (reg & 0x7F))
        return -3;
    *v = ((uint32_t)in[3] << 24) | ((uint32_t)in[4] << 16) | ((uint32_t)in[5] << 8) | in[6];
    return 0;
}

int tmc_mres_code(uint32_t microsteps)
{
    for (int code = 0; code <= 8; code++)
        if ((256u >> code) == microsteps)
            return code;
    return -1;
}

uint32_t tmc_chopconf(int mres_code, int dedge)
{
    uint32_t v = TMC_CHOPCONF_DEFAULT & ~((0xFu << 24) | (1u << 29));
    return v | ((uint32_t)(mres_code & 0xF) << 24) | (dedge ? 1u << 29 : 0);
}

uint32_t tmc_mscnt_per_step(int mres_code)
{
    return 1u << mres_code;
}

/* I = (CS+1)/32 * 325 mV / (R + 20 mOhm) / sqrt 2, so CS + 1 = I * 32 * sqrt 2 * (R + 20) / 325,
 * with I in mA and R in mOhm: (CS + 1) = I * 32 * 1414 * (R + 20) / (325 * 10^6), rounded */
uint32_t tmc_cs_for_ma(uint32_t ma, uint32_t rsense_mohm)
{
    uint64_t num = (uint64_t)ma * 32u * 1414u * (rsense_mohm + 20u);
    uint64_t den = 325000000u;
    uint64_t cs1 = (num + den / 2) / den;
    if (cs1 < 1)
        cs1 = 1;
    if (cs1 > 32)
        cs1 = 32;
    return (uint32_t)cs1 - 1;
}

uint32_t tmc_ma_for_cs(uint32_t cs, uint32_t rsense_mohm)
{
    uint64_t num = (uint64_t)(cs + 1) * 325000000u;
    uint64_t den = (uint64_t)32u * 1414u * (rsense_mohm + 20u);
    return (uint32_t)((num + den / 2) / den);
}

uint32_t tmc_ihold_irun(uint32_t ihold, uint32_t irun, uint32_t iholddelay)
{
    return (ihold & 31u) | ((irun & 31u) << 8) | ((iholddelay & 15u) << 16);
}
