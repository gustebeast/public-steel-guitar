/* output_panel BENCH firmware: the Pi's samples to the jack.
 *
 * Runs as the application under the USB loader (boot.c). The board shows up as one serial port.
 * The Pi sends stereo samples and this plays them; nothing here knows where they came from
 * (bench/publicbench/panel.py does the listening). The DAC and ADC run from the same clock, I2S2
 * as master into the PCM5102A, I2S3 as a slave off the same wires from the PCM1808.
 *
 * The sample rate is PLL3's nearest to 48 kHz, 48077 Hz (`?` says), not 48000: the host fits to it.
 * THE DAC IS THE CLOCK. Samples the ring has no room for wait in USB (the host's write blocks),
 * so a host that sends as fast as it can runs exactly at the DAC's rate. A ring that runs out plays
 * silence and counts it.
 *
 * Lines from the host (ASCII, '\n', decimal):
 *   ?                  -> I public-steel-guitar-output-bench <version> fs=<Hz> rev=<board>
 *   A <bytes>          then that many raw bytes: int16 little-endian, left then right. No reply
 *   S                  -> S <frames played> <frames queued> <frames short> <adc peak L> <adc peak R> <t_us>
 *   R <0|1>            relay: 0 direct (the pickup, no firmware in the path), 1 processed (the DAC)
 *   P <tip> <ring>     output level, 0..255; the same 0x80 as power-up until first written
 *   J <0|1>            jack: 0 balanced (R37's rest state), 1 stereo
 *   B                  -> OK, then back to the loader
 * R2 only (built REV=2):
 *   U                  -> U <attached: 0 none, 1 we source, 2 we sink, 3 accessory> <setting>
 *                         <fault 0|1> <host forced 0|1> <current the far end offers, 0..3>
 *   M <0|1|2>          J1's setting: 0 auto (dual role, Try.SNK), 1 host only, 2 device only
 *   H <0|1>            host forced: J1 hosts a device with no Rd (setting 1 only). VBUS still
 *                      goes only through the hardware gate
 *   V                  -> V <inlet mV> <inlet mA>
 * Lines to the host: OK, or E <what>. */
#include <stdlib.h>
#include <string.h>
#include "UART.h"
#include "ch32v30x_usbhs_device.h"
#include "link.h"

#ifndef REV
#define REV 1
#endif
#if REV == 1
#define CS_PORT  GPIOA
#define CS_PIN   GPIO_Pin_5
#define SCK_PORT GPIOA
#define SCK_PIN  GPIO_Pin_4
#define SDI_PORT GPIOB
#define SDI_PIN  GPIO_Pin_0
#else
#define CS_PORT  GPIOC
#define CS_PIN   GPIO_Pin_9
#define SCK_PORT GPIOA
#define SCK_PIN  GPIO_Pin_8
#define SDI_PORT GPIOC
#define SDI_PIN  GPIO_Pin_8
#endif
#define RELAY_PIN GPIO_Pin_5        /* PC5 */
#define JACK_PIN  GPIO_Pin_1        /* PB1. PB2 is on the same net and stays an input for ever */

void NMI_Handler(void) __attribute__((interrupt));
void HardFault_Handler(void) __attribute__((interrupt));
void NMI_Handler(void) { }
void HardFault_Handler(void) { NVIC_SystemReset(); while (1) { } }

/* ---- samples: both rings circular under DMA, counted in channels (one int16 each) ---- */
#define TX_N 2048                   /* 1024 frames, 21 ms */
#define RX_N 960
#define GAP  96                     /* how far ahead of the DAC a restart lands: 1 ms */
#define TX_DMA DMA1_Channel5
#define RX_DMA DMA2_Channel1

__attribute__((aligned(4))) static int16_t tx[TX_N], rx[RX_N];
static uint32_t rd, wr, played, shortfall, fs;
static int32_t queued;

/* where the DAC has got to. What it has played goes back to zero, so a host that stops leaves
 * silence behind and not the ring going round. Has to run every 21 ms. */
static void track(void)
{
    uint32_t pos = (TX_N - TX_DMA->CNTR) % TX_N;
    uint32_t d = (pos + TX_N - rd) % TX_N;
    while (rd != pos) { tx[rd] = 0; rd = (rd + 1) % TX_N; }
    played += d; queued -= (int32_t)d;
    if (queued < 0) {
        shortfall += (uint32_t)-queued;
        queued = GAP;
        wr = (pos + GAP) & (TX_N - 2);
    }
}

static void dma(DMA_Channel_TypeDef *ch, uint32_t per, int16_t *mem, uint16_t n, uint32_t dir)
{
    DMA_InitTypeDef d = {0};
    DMA_DeInit(ch);
    d.DMA_PeripheralBaseAddr = per;
    d.DMA_MemoryBaseAddr = (uint32_t)mem;
    d.DMA_DIR = dir;
    d.DMA_BufferSize = n;
    d.DMA_PeripheralInc = DMA_PeripheralInc_Disable;
    d.DMA_MemoryInc = DMA_MemoryInc_Enable;
    d.DMA_PeripheralDataSize = DMA_PeripheralDataSize_HalfWord;
    d.DMA_MemoryDataSize = DMA_MemoryDataSize_HalfWord;
    d.DMA_Mode = DMA_Mode_Circular;
    d.DMA_Priority = DMA_Priority_VeryHigh;
    d.DMA_M2M = DMA_M2M_Disable;
    DMA_Init(ch, &d);
    DMA_Cmd(ch, ENABLE);
}

/* MCK = 256 fs into both converters. 16 bits in a 32-bit channel: BCK = 64 fs, which is what
 * the PCM1808 wants as a slave, with one halfword per channel. 96 MHz has no divider near
 * 48 kHz, so PLL3 and the divider are set here: 8 MHz x 10 = 80, its VCO 160 MHz,
 * / (256 x 13) = 48077 Hz. */
static void audio_init(void)
{
    GPIO_InitTypeDef g = {0};
    I2S_InitTypeDef s = {0};
    uint32_t n = 13, src = RCC_I2S2CLKSource_PLL3_VCO;

    RCC_PREDIV2Config(RCC_PREDIV2_Div1);
    RCC_PLL3Config(RCC_PLL3Mul_10);
    RCC_PLL3Cmd(ENABLE);
    for (int i = 0; RCC_GetFlagStatus(RCC_FLAG_PLL3RDY) == RESET; i++)
        if (i > 1000000) { n = 8; src = RCC_I2S2CLKSource_SYSCLK; break; }  /* 46875 Hz */
    fs = (src == RCC_I2S2CLKSource_SYSCLK ? SystemCoreClock : 160000000u) / (256 * n);
    RCC_I2S2CLKConfig(src);
    RCC_I2S3CLKConfig(src);

    RCC_APB1PeriphClockCmd(RCC_APB1Periph_SPI2 | RCC_APB1Periph_SPI3, ENABLE);
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_AFIO, ENABLE);
    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_DMA1 | RCC_AHBPeriph_DMA2, ENABLE);

    g.GPIO_Speed = GPIO_Speed_50MHz;
    g.GPIO_Mode = GPIO_Mode_AF_PP;
    g.GPIO_Pin = GPIO_Pin_12 | GPIO_Pin_13 | GPIO_Pin_15;
    GPIO_Init(GPIOB, &g);
    g.GPIO_Pin = GPIO_Pin_6;
    GPIO_Init(GPIOC, &g);
    g.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    g.GPIO_Pin = GPIO_Pin_15;
    GPIO_Init(GPIOA, &g);
    g.GPIO_Pin = GPIO_Pin_3 | GPIO_Pin_5;
    GPIO_Init(GPIOB, &g);

    s.I2S_Standard = I2S_Standard_Phillips;
    s.I2S_DataFormat = I2S_DataFormat_16bextended;
    s.I2S_AudioFreq = I2S_AudioFreq_48k;
    s.I2S_CPOL = I2S_CPOL_Low;
    s.I2S_Mode = I2S_Mode_SlaveRx;
    s.I2S_MCLKOutput = I2S_MCLKOutput_Disable;
    I2S_Init(SPI3, &s);
    s.I2S_Mode = I2S_Mode_MasterTx;
    s.I2S_MCLKOutput = I2S_MCLKOutput_Enable;
    I2S_Init(SPI2, &s);
    SPI2->I2SPR = (uint16_t)((1u << 9) | ((n & 1) << 8) | (n / 2));

    dma(RX_DMA, (uint32_t)&SPI3->DATAR, rx, RX_N, DMA_DIR_PeripheralSRC);
    dma(TX_DMA, (uint32_t)&SPI2->DATAR, tx, TX_N, DMA_DIR_PeripheralDST);
    SPI_I2S_DMACmd(SPI3, SPI_I2S_DMAReq_Rx, ENABLE);
    SPI_I2S_DMACmd(SPI2, SPI_I2S_DMAReq_Tx, ENABLE);
    I2S_Cmd(SPI3, ENABLE);          /* the slave first, so it sees the master's first frame */
    I2S_Cmd(SPI2, ENABLE);
}

/* ---- the panel's pins -------------------------------------------------------------- */
static uint8_t level[2] = {0x80, 0x80};

static void wait_us(uint32_t n)
{
    uint64_t end = now_us() + n;
    while (now_us() < end) track();
}

/* U10: ten bits, address then data, MSB first, clocked on the rising edge, latched when CS
 * rises. Bit-banged at about 100 kHz. Never a CS pulse without a full word. */
static void pot_word(uint8_t ch, uint8_t val)
{
    uint16_t w = (uint16_t)((ch << 8) | val);
    GPIO_ResetBits(CS_PORT, CS_PIN);
    for (int i = 9; i >= 0; i--) {
        GPIO_WriteBit(SDI_PORT, SDI_PIN, (w >> i) & 1 ? Bit_SET : Bit_RESET);
        Delay_Us(5);
        GPIO_SetBits(SCK_PORT, SCK_PIN);
        Delay_Us(5);
        GPIO_ResetBits(SCK_PORT, SCK_PIN);
    }
    Delay_Us(5);
    GPIO_SetBits(CS_PORT, CS_PIN);
    Delay_Us(5);
}

static void pot_set(uint8_t tip, uint8_t ring) { pot_word(0, tip); pot_word(1, ring); }

/* DIRECT_AC floats while the relay is energised, up to 2.4 V of step: pot at 00H around a
 * release, 100 ms, then the level back. */
static void relay_set(int on)
{
    if (on) { GPIO_SetBits(GPIOC, RELAY_PIN); return; }
    if (!GPIO_ReadOutputDataBit(GPIOC, RELAY_PIN)) return;
    pot_set(0, 0);
    GPIO_ResetBits(GPIOC, RELAY_PIN);
    wait_us(100000);
    pot_set(level[0], level[1]);
}

static void pins_init(void)
{
    GPIO_InitTypeDef g = {0};
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_GPIOB | RCC_APB2Periph_GPIOC, ENABLE);
    g.GPIO_Speed = GPIO_Speed_10MHz;
    g.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_SetBits(CS_PORT, CS_PIN);  /* high in the register BEFORE it is an output */
    g.GPIO_Pin = CS_PIN;
    GPIO_Init(CS_PORT, &g);
    GPIO_ResetBits(SCK_PORT, SCK_PIN);
    g.GPIO_Pin = SCK_PIN;
    GPIO_Init(SCK_PORT, &g);
    GPIO_ResetBits(SDI_PORT, SDI_PIN);
    g.GPIO_Pin = SDI_PIN;
    GPIO_Init(SDI_PORT, &g);
    GPIO_ResetBits(GPIOC, RELAY_PIN);
    g.GPIO_Pin = RELAY_PIN;
    GPIO_Init(GPIOC, &g);
    GPIO_ResetBits(GPIOB, JACK_PIN);
    g.GPIO_Pin = JACK_PIN;
    GPIO_Init(GPIOB, &g);
}

#if REV != 1
/* ---- R2: J1, the dual-role USB-C port, and the inlet meter (work items R2-2, R2-4) ---------
 * U13 (TUSB320LAI, ADDR high: 0x67) and U16 (INA226, 0x40) on PB10 SCL / PB11 SDA, bit-banged
 * open drain against R50/R51. U15's FAULT# is PA3, U13's INT_N PC4, the role net PD8.
 *
 * THE SAFETY IS NOT HERE. The gate in hardware (elec/output_panel.py _r2_ports: Q4-Q6, U15)
 * decides whether J1 sources VBUS: never onto a VBUS already present, never past U15's limit,
 * never backwards. What this adds is what only a register can say -- Try.SNK, so a dual-role
 * laptop or phone makes us the device, and the 1.5 A advertisement -- and the UI's setting.
 * With no firmware the port is a plain DRP at default current, and works.
 *
 * Register map: TI SLLSEQ8D pp.17-19 (read 2026-11-03). 0x08 bits 7:6 CURRENT_MODE_ADVERTISE,
 * 5:4 CURRENT_MODE_DETECT. 0x09 bits 7:6 ATTACHED_STATE, 4 INTERRUPT_STATUS (write 1 to clear).
 * 0x0A bits 5:4 MODE_SELECT, 2:1 SOURCE_PREF, 0 DISABLE_TERM. A mode change takes p.14's
 * sequence: DISABLE_TERM, the mode, 5 ms, DISABLE_TERM off. */
#define SCL_PIN   GPIO_Pin_10       /* PB10 */
#define SDA_PIN   GPIO_Pin_11       /* PB11 */
#define FAULT_PIN GPIO_Pin_3        /* PA3, U15 FAULT#, R48 up */
#define RINT_PIN  GPIO_Pin_4        /* PC4, U13 INT_N, R49 up */
#define ID_PIN    GPIO_Pin_8        /* PD8, ROLE_ID_N, R43 up */
#define TUSB      0x67
#define INA       0x40
#define TRY_SNK   0x02              /* SOURCE_PREF 01 */

static void i2c_l(uint16_t pin, int v)
{
    GPIO_WriteBit(GPIOB, pin, v ? Bit_SET : Bit_RESET);     /* open drain: 1 lets go */
    Delay_Us(5);
}

static void i2c_start(void) { i2c_l(SDA_PIN, 1); i2c_l(SCL_PIN, 1); i2c_l(SDA_PIN, 0); i2c_l(SCL_PIN, 0); }
static void i2c_stop(void) { i2c_l(SDA_PIN, 0); i2c_l(SCL_PIN, 1); i2c_l(SDA_PIN, 1); }

static int i2c_tx(uint8_t b)        /* 1 if the byte was acked */
{
    for (int i = 7; i >= 0; i--) { i2c_l(SDA_PIN, (b >> i) & 1); i2c_l(SCL_PIN, 1); i2c_l(SCL_PIN, 0); }
    i2c_l(SDA_PIN, 1);
    i2c_l(SCL_PIN, 1);
    int ack = !GPIO_ReadInputDataBit(GPIOB, SDA_PIN);
    i2c_l(SCL_PIN, 0);
    return ack;
}

static uint8_t i2c_rx(int more)
{
    uint8_t b = 0;
    i2c_l(SDA_PIN, 1);
    for (int i = 0; i < 8; i++) {
        i2c_l(SCL_PIN, 1);
        b = (uint8_t)((b << 1) | GPIO_ReadInputDataBit(GPIOB, SDA_PIN));
        i2c_l(SCL_PIN, 0);
    }
    i2c_l(SDA_PIN, !more);
    i2c_l(SCL_PIN, 1);
    i2c_l(SCL_PIN, 0);
    i2c_l(SDA_PIN, 1);
    return b;
}

/* n bytes to or from a register, MSB first (the INA226's are 16 bits). 0, or -1 on a nack */
static int i2c_put(uint8_t dev, uint8_t reg, const uint8_t *d, int n)
{
    i2c_start();
    int ok = i2c_tx((uint8_t)(dev << 1)) && i2c_tx(reg);
    for (int i = 0; ok && i < n; i++) ok = i2c_tx(d[i]);
    i2c_stop();
    return ok ? 0 : -1;
}

static int i2c_get(uint8_t dev, uint8_t reg, uint8_t *d, int n)
{
    i2c_start();
    int ok = i2c_tx((uint8_t)(dev << 1)) && i2c_tx(reg);
    if (ok) { i2c_start(); ok = i2c_tx((uint8_t)((dev << 1) | 1)); }
    for (int i = 0; ok && i < n; i++) d[i] = i2c_rx(i < n - 1);
    i2c_stop();
    return ok ? 0 : -1;
}

static uint8_t port_mode;           /* the UI's setting: 0 auto, 1 host, 2 device */
static uint8_t id_forced;
static const uint8_t mode_bits[3] = {0x00, 0x20, 0x10};   /* PORT pin (open: DRP), DFP, UFP */

static void id_force(int on)
{
    GPIO_InitTypeDef g = {0};
    g.GPIO_Pin = ID_PIN;
    g.GPIO_Speed = GPIO_Speed_10MHz;
    g.GPIO_Mode = on ? GPIO_Mode_Out_OD : GPIO_Mode_IN_FLOATING;
    GPIO_ResetBits(GPIOD, ID_PIN);  /* low in the register BEFORE it drives */
    GPIO_Init(GPIOD, &g);
    id_forced = (uint8_t)(on != 0);
}

/* At start-up: 1.5 A (U15 limits at 1.61 to 1.80) and Try.SNK. MODE_SELECT stays on the PORT
 * pin, so a host already attached is not dropped by a firmware start. */
static int port_init(void)
{
    uint8_t d = 0x40;
    if (i2c_put(TUSB, 0x08, &d, 1)) return -1;
    d = TRY_SNK;
    return i2c_put(TUSB, 0x0A, &d, 1);
}

static int port_mode_set(uint8_t m)
{
    uint8_t d = (uint8_t)(mode_bits[m] | TRY_SNK | 1);
    if (m != 1 && id_forced) id_force(0);
    if (i2c_put(TUSB, 0x0A, &d, 1)) return -1;
    wait_us(5000);
    d &= (uint8_t)~1;
    if (i2c_put(TUSB, 0x0A, &d, 1)) return -1;
    port_mode = m;
    return 0;
}

static void port_pins_init(void)
{
    GPIO_InitTypeDef g = {0};
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOD, ENABLE);
    g.GPIO_Speed = GPIO_Speed_10MHz;
    g.GPIO_Mode = GPIO_Mode_Out_OD;
    GPIO_SetBits(GPIOB, SCL_PIN | SDA_PIN);
    g.GPIO_Pin = SCL_PIN | SDA_PIN;
    GPIO_Init(GPIOB, &g);
    g.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    g.GPIO_Pin = FAULT_PIN;
    GPIO_Init(GPIOA, &g);
    g.GPIO_Pin = RINT_PIN;
    GPIO_Init(GPIOC, &g);
    id_force(0);
}
#endif

/* ---- the host ---------------------------------------------------------------------- */
static char *w_dec(char *p, uint64_t v)
{
    char t[20]; int n = 0;
    do { t[n++] = (char)('0' + v % 10); v /= 10; } while (v);
    while (n) *p++ = t[--n];
    return p;
}

static uint32_t audio_left;         /* raw bytes still to come */
static uint8_t odd, low;

static void status(void)
{
    char l[96], *p = l;
    int pk[2] = {0, 0};
    for (int i = 0; i < RX_N; i++) {
        int v = abs(rx[i]);
        if (v > pk[i & 1]) pk[i & 1] = v;
    }
    *p++ = 'S'; *p++ = ' ';
    p = w_dec(p, played / 2); *p++ = ' ';
    p = w_dec(p, (uint32_t)queued / 2); *p++ = ' ';
    p = w_dec(p, shortfall / 2); *p++ = ' ';
    p = w_dec(p, (uint32_t)pk[0]); *p++ = ' ';
    p = w_dec(p, (uint32_t)pk[1]); *p++ = ' ';
    p = w_dec(p, now_us()); *p++ = '\n';
    link_send(l, (uint16_t)(p - l));
}

static void line(char *s)
{
    char c = s[0], *e = s + 1, l[96], *p = l;
    uint32_t a = strtoul(e, &e, 10), b = strtoul(e, &e, 10);
    switch (c) {
    case '?':
        static const char id[] = "I public-steel-guitar-output-bench ";
        memcpy(p, id, sizeof id - 1); p += sizeof id - 1;
        strcpy(p, VERSION); p += strlen(VERSION);
        memcpy(p, " fs=", 4); p += 4;
        p = w_dec(p, fs);
        memcpy(p, " rev=", 5); p += 5;
        p = w_dec(p, REV); *p++ = '\n';
        link_send(l, (uint16_t)(p - l));
        return;
    case 'A':
        if (a & 1) break;
        audio_left = a; odd = 0;
        return;
    case 'S': status(); return;
    case 'R': relay_set(a != 0); break;
    case 'J': GPIO_WriteBit(GPIOB, JACK_PIN, a ? Bit_SET : Bit_RESET); break;
    case 'P':
        if (a > 255 || b > 255) { link_say("E level\n"); return; }
        level[0] = (uint8_t)a; level[1] = (uint8_t)b;
        pot_set(level[0], level[1]);
        break;
#if REV != 1
    case 'U': {                     /* J1: attached state, setting, fault, forced, advert seen */
        uint8_t r8, r9;
        if (i2c_get(TUSB, 0x08, &r8, 1) || i2c_get(TUSB, 0x09, &r9, 1)) { link_say("E port\n"); return; }
        if (r9 & 0x10) { uint8_t c = 0x10; i2c_put(TUSB, 0x09, &c, 1); }   /* INT_N let go */
        *p++ = 'U'; *p++ = ' ';
        p = w_dec(p, r9 >> 6); *p++ = ' ';
        p = w_dec(p, port_mode); *p++ = ' ';
        p = w_dec(p, !GPIO_ReadInputDataBit(GPIOA, FAULT_PIN)); *p++ = ' ';
        p = w_dec(p, id_forced); *p++ = ' ';
        p = w_dec(p, (r8 >> 4) & 3); *p++ = '\n';
        link_send(l, (uint16_t)(p - l));
        return;
    }
    case 'M':
        if (a > 2) { link_say("E mode\n"); return; }
        if (port_mode_set((uint8_t)a)) { link_say("E port\n"); return; }
        break;
    case 'H':                       /* force host: the host setting only, through the same gate */
        if (a && port_mode != 1) { link_say("E mode\n"); return; }
        id_force(a != 0);
        break;
    case 'V': {                     /* inlet: bus mV (1.25 mV a count), mA (2.5 uV over 5 mohm) */
        uint8_t v[2], s[2];
        if (i2c_get(INA, 0x02, v, 2) || i2c_get(INA, 0x01, s, 2)) { link_say("E meter\n"); return; }
        int32_t mv = ((v[0] << 8) | v[1]) * 5 / 4, ma = (int16_t)((s[0] << 8) | s[1]) / 2;
        *p++ = 'V'; *p++ = ' ';
        p = w_dec(p, (uint32_t)mv); *p++ = ' ';
        if (ma < 0) { *p++ = '-'; ma = -ma; }
        p = w_dec(p, (uint32_t)ma); *p++ = '\n';
        link_send(l, (uint16_t)(p - l));
        return;
    }
#endif
    case 'B':
        relay_set(0);
        link_say("OK\n");
        Delay_Ms(20);
        reset_to(GO_LOADER);
        return;
    default: link_say("E line\n"); return;
    }
    link_say("OK\n");
}

static void byte_in(uint8_t c)
{
    static char ln[32]; static uint8_t n;
    if (audio_left) {
        audio_left--;
        if (!odd) { low = c; odd = 1; return; }
        odd = 0;
        tx[wr] = (int16_t)(uint16_t)(low | (c << 8));
        wr = (wr + 1) % TX_N;
        queued++;
        return;
    }
    if (c == '\r') return;
    if (c == '\n') { ln[n] = 0; if (n) line(ln); n = 0; }
    else if (n < sizeof ln - 1) ln[n++] = (char)c;
}

int main(void)
{
    static uint8_t pkt[DEF_USB_HS_PACK_LEN];
    pins_init();
    link_init();
    audio_init();
#if REV != 1
    port_pins_init();
    port_init();                    /* a silent U13 shows as E port on U; J1 still works */
#endif
    while (1) {
        track();
        if (queued + DEF_USB_HS_PACK_LEN / 2 > TX_N - 8) continue;      /* wait in USB */
        IWDG_ReloadCounter();             /* boot.c started it; fed only where USB is heard */
        int got = link_take(pkt);
        for (int i = 0; i < got; i++) byte_in(pkt[i]);
    }
}
