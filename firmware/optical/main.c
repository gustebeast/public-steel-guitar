/* optical board BENCH firmware: the converters' samples, untouched, to the host.
 *
 * The board (STM32H743IIT6, 25 MHz crystal, USB3300 high-speed PHY) shows up as TWO serial
 * ports. The first takes one-line commands; the second carries the samples. Nothing is
 * demodulated or detected here: the five TLV320ADC3140s run at 192 kHz, the emitters are
 * gated at 48 kHz from the same clock, and whichever converters the host asks for are sent
 * as they come. Lock-in, SUM / DIFF and pitch are done on the host (bench/psgbench), after
 * the fact, where they can be changed without reflashing.
 *
 * THE SAMPLE COUNT IS THE CLOCK. Every block says which sample it starts at, counted from
 * when the converters were started, and `T` answers with the count now. The host lines that
 * count up with its own clock, and with the motor controller's.
 *
 * Control port, lines from the host (decimal unless said):
 *   ?                 -> I psg-optical-bench <version> fs=192000 block=<frames> slots=4
 *   T                 -> T <sample count now>
 *   L <mask>          which converters to send: bit k = converter k (U14 + k); 0 stops
 *   E <0|1>           emitters off / gated at 48 kHz (default 1)
 *   W <page> <reg> <value>   write one converter register, all five at once (hex)
 *   R                 configure the converters again from reset
 *   F <0|1> <0|1>     frame sync one bit early (1) or with the first bit (0); sample on the
 *                     falling (1) or rising (0) clock edge. Restarts the stream.
 * Lines to the host:  OK ..., E <what>, and at start-up one line per step that failed.
 *
 * Sample port: blocks, each
 *   'P' 'S' 'G' 'O', u8 mask, u8 flags (bit 0: a block before this one was dropped),
 *   u16 frames, u64 first sample -- then for each converter in the mask, lowest first,
 *   frames x 4 slots of int16, little-endian.
 *
 * NOT YET RUN ON A BOARD (2026-10-13). It compiles, and the converter registers were read
 * off TI's SBAS993B. The frame format the converters and the SAI agree on (the F command's
 * two choices) is a reading of two datasheets and has not met a signal.
 */
#include <string.h>
#include "stm32h7xx_hal.h"
#include "tusb.h"

#define VERSION   1
#define FS        192000
#define SLOTS     4
#define FRAMES    960                     /* a block: 5 ms */
#define LANES     5
#define HALF      (FRAMES * SLOTS)        /* samples in a block of one converter */

/* ---- clocks: everything audio from PLL1, so the carrier and the frame sync are locked -- */
static int clock_setup(void)
{
    HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);
    while (!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) { }
    RCC_OscInitTypeDef o = {0};
    o.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    o.HSEState = RCC_HSE_ON;
    o.PLL.PLLState = RCC_PLL_ON;
    o.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    o.PLL.PLLM = 5;                       /* 25 MHz / 5 = 5 MHz */
    o.PLL.PLLN = 157;                     /* x 157.2864 = 786.432 MHz */
    o.PLL.PLLFRACN = 2346;                /* .2864 x 8192 */
    o.PLL.PLLP = 4;                       /* 196.608 MHz: the core, and 4096 x 48 kHz */
    o.PLL.PLLQ = 16;                      /* 49.152 MHz: the SAI kernel, 4 x the bit clock */
    o.PLL.PLLR = 4;
    o.PLL.PLLRGE = RCC_PLL1VCIRANGE_2;
    o.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
    if (HAL_RCC_OscConfig(&o) != HAL_OK) return -1;
    RCC_ClkInitTypeDef c = {0};
    c.ClockType = RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_D1PCLK1
                | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2 | RCC_CLOCKTYPE_D3PCLK1;
    c.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    c.SYSCLKDivider = RCC_SYSCLK_DIV1;
    c.AHBCLKDivider = RCC_HCLK_DIV1;      /* 196.608 MHz */
    c.APB3CLKDivider = RCC_APB3_DIV2;
    c.APB1CLKDivider = RCC_APB1_DIV2;     /* 98.304 MHz; its timers run at twice that */
    c.APB2CLKDivider = RCC_APB2_DIV2;
    c.APB4CLKDivider = RCC_APB4_DIV2;
    if (HAL_RCC_ClockConfig(&c, FLASH_LATENCY_2) != HAL_OK) return -1;
    RCC_PeriphCLKInitTypeDef p = {0};
    p.PeriphClockSelection = RCC_PERIPHCLK_SAI1 | RCC_PERIPHCLK_SAI23;
    p.Sai1ClockSelection = RCC_SAI1CLKSOURCE_PLL;       /* PLL1 Q */
    p.Sai23ClockSelection = RCC_SAI23CLKSOURCE_PLL;
    return HAL_RCCEx_PeriphCLKConfig(&p) == HAL_OK ? 0 : -1;
}

void SysTick_Handler(void) { HAL_IncTick(); }

/* ---- pins ------------------------------------------------------------------------------ */
static void pin(GPIO_TypeDef *port, uint32_t pins, uint32_t mode, uint32_t speed, uint32_t af)
{
    GPIO_InitTypeDef g = {0};
    g.Pin = pins; g.Mode = mode; g.Pull = GPIO_NOPULL; g.Speed = speed; g.Alternate = af;
    HAL_GPIO_Init(port, &g);
}

static void pins_setup(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE(); __HAL_RCC_GPIOB_CLK_ENABLE(); __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE(); __HAL_RCC_GPIOE_CLK_ENABLE(); __HAL_RCC_GPIOF_CLK_ENABLE();
    __HAL_RCC_GPIOH_CLK_ENABLE(); __HAL_RCC_GPIOI_CLK_ENABLE();
    /* the PHY: D0 PA3, D1 PB0, D2 PB1, D3 PB10, D4 PB11, D5 PB12, D6 PB13, D7 PB5,
       CK PA5, STP PC0, DIR PI11, NXT PH4 (elec/optical.py ULPI) */
    const uint32_t V = GPIO_SPEED_FREQ_VERY_HIGH;
    pin(GPIOA, GPIO_PIN_3 | GPIO_PIN_5, GPIO_MODE_AF_PP, V, GPIO_AF10_OTG2_HS);
    pin(GPIOB, GPIO_PIN_0 | GPIO_PIN_1 | GPIO_PIN_5 | GPIO_PIN_10 | GPIO_PIN_11 | GPIO_PIN_12
               | GPIO_PIN_13, GPIO_MODE_AF_PP, V, GPIO_AF10_OTG2_HS);
    pin(GPIOC, GPIO_PIN_0, GPIO_MODE_AF_PP, V, GPIO_AF10_OTG2_HS);
    pin(GPIOI, GPIO_PIN_11, GPIO_MODE_AF_PP, V, GPIO_AF10_OTG2_HS);
    pin(GPIOH, GPIO_PIN_4, GPIO_MODE_AF_PP, V, GPIO_AF10_OTG2_HS);
    /* the converters: SCK PE5, FS PE4 (medium drive, by the board's notes), data PE6 PE3
       PA0 PI6 PD1 */
    const uint32_t M = GPIO_SPEED_FREQ_MEDIUM;
    pin(GPIOE, GPIO_PIN_4 | GPIO_PIN_5 | GPIO_PIN_6 | GPIO_PIN_3, GPIO_MODE_AF_PP, M, GPIO_AF6_SAI1);
    pin(GPIOA, GPIO_PIN_0, GPIO_MODE_AF_PP, M, GPIO_AF10_SAI2);
    pin(GPIOI, GPIO_PIN_6, GPIO_MODE_AF_PP, M, GPIO_AF10_SAI2);
    pin(GPIOD, GPIO_PIN_1, GPIO_MODE_AF_PP, M, GPIO_AF6_SAI3);
    /* their I2C, driven by hand: PF0 SDA, PF1 SCL, open drain on the board's pull-ups */
    HAL_GPIO_WritePin(GPIOF, GPIO_PIN_0 | GPIO_PIN_1, GPIO_PIN_SET);
    pin(GPIOF, GPIO_PIN_0 | GPIO_PIN_1, GPIO_MODE_OUTPUT_OD, GPIO_SPEED_FREQ_LOW, 0);
    /* the emitter gate, PB3 = TIM2_CH2; low (emitters off) until the timer has it */
    pin(GPIOB, GPIO_PIN_3, GPIO_MODE_AF_PP, GPIO_SPEED_FREQ_LOW, GPIO_AF1_TIM2);
    /* TP12, the debug serial out: PA2 = USART2_TX */
    pin(GPIOA, GPIO_PIN_2, GPIO_MODE_AF_PP, GPIO_SPEED_FREQ_LOW, GPIO_AF7_USART2);
}

/* ---- TP12: 115200 8N1, for what cannot be said over a USB that is not up -------------- */
static void dbg_setup(void)
{
    __HAL_RCC_USART2_CLK_ENABLE();
    USART2->BRR = (HAL_RCC_GetPCLK1Freq() + 57600) / 115200;
    USART2->CR1 = USART_CR1_TE | USART_CR1_UE;
}

static void dbg(const char *s)
{
    for (; *s; s++) {
        while (!(USART2->ISR & USART_ISR_TXE_TXFNF)) { }
        USART2->TDR = (uint8_t)*s;
    }
}

/* ---- the converters' I2C, bit by bit (about 50 kHz; writes only) ----------------------- */
#define SDA GPIO_PIN_0
#define SCL GPIO_PIN_1
#define ADC_ADDR 0x4C                     /* all five answer here, by their straps */

static void i2c_wait(void) { for (volatile int i = 0; i < 400; i++) { } }
static void i2c_set(uint16_t p, int v) { HAL_GPIO_WritePin(GPIOF, p, v ? GPIO_PIN_SET : GPIO_PIN_RESET); i2c_wait(); }

static int i2c_byte(uint8_t b)
{
    for (int i = 7; i >= 0; i--) { i2c_set(SDA, (b >> i) & 1); i2c_set(SCL, 1); i2c_set(SCL, 0); }
    i2c_set(SDA, 1); i2c_set(SCL, 1);
    int ack = HAL_GPIO_ReadPin(GPIOF, SDA) == GPIO_PIN_RESET;
    i2c_set(SCL, 0);
    return ack;
}

static int i2c_write(uint8_t reg, uint8_t val)
{
    i2c_set(SDA, 0); i2c_set(SCL, 0);                                   /* start */
    int ok = i2c_byte(ADC_ADDR << 1) & i2c_byte(reg) & i2c_byte(val);
    i2c_set(SDA, 0); i2c_set(SCL, 1); i2c_set(SDA, 1);                  /* stop */
    return ok ? 0 : -1;
}

static void i2c_free(void)
{   /* a debugger reset can land mid-transfer and leave a converter holding SDA low */
    for (int i = 0; i < 9 && HAL_GPIO_ReadPin(GPIOF, SDA) == GPIO_PIN_RESET; i++) {
        i2c_set(SCL, 0); i2c_set(SCL, 1);
    }
    i2c_set(SCL, 0); i2c_set(SDA, 0); i2c_set(SCL, 1); i2c_set(SDA, 1);
}

/* TLV320ADC3140 (TI SBAS993B, section 8.6), page 0. The converter is the clock SLAVE and makes its own
   internal clocks from the bit clock and frame sync it is given. */
static int adc_setup(void)
{
    static const uint8_t cfg[][2] = {
        {0x00, 0x00},       /* page 0 */
        {0x02, 0x81},       /* SLEEP_CFG: AREG from the internal regulator (AVDD is 3.3 V), awake */
        {0x07, 0x00},       /* ASI_CFG0: TDM, 16-bit words */
        {0x08, 0x01},       /* ASI_CFG1: TX_OFFSET 1. At 0 the first bit follows the frame sync's
                               own edge, half a bit clock (40 ns) before it is sampled; at 1
                               every bit changes on a rising edge, one clock after the sync */
        {0x0B, 0x00}, {0x0C, 0x01}, {0x0D, 0x02}, {0x0E, 0x03},    /* channel n in slot n-1 */
        {0x3C, 0xA8}, {0x41, 0xA8}, {0x46, 0xA8}, {0x4B, 0xA8},    /* CHn_CFG0: line, single-ended, AC, 20 k */
        {0x73, 0xF0},       /* IN_CH_EN: 1..4 */
        {0x74, 0xF0},       /* ASI_OUT_CH_EN: 1..4 */
        {0x75, 0x60},       /* PWR_CFG: converters and PLL on, no mic bias */
    };
    i2c_free();
    int bad = 0;
    bad |= i2c_write(0x00, 0x00);
    bad |= i2c_write(0x01, 0x01);         /* SW_RESET: SHDNZ is tied high on this board */
    HAL_Delay(10);
    for (unsigned i = 0; i < sizeof cfg / sizeof cfg[0]; i++) {
        bad |= i2c_write(cfg[i][0], cfg[i][1]);
        if (cfg[i][0] == 0x02) HAL_Delay(2);
    }
    return bad;
}

/* ---- the emitters: TIM2 channel 2, 196.608 MHz / 4096 = 48 kHz, half on ---------------- */
static uint8_t emit_on = 1;

static void emit(int on)
{
    emit_on = on != 0;
    __HAL_RCC_TIM2_CLK_ENABLE();
    TIM2->CR1 = 0;
    TIM2->PSC = 0; TIM2->ARR = 4095; TIM2->CCR2 = on ? 2048 : 0;
    TIM2->CCMR1 = (6u << TIM_CCMR1_OC2M_Pos) | TIM_CCMR1_OC2PE;        /* PWM 1 */
    TIM2->CCER = TIM_CCER_CC2E;
    TIM2->EGR = TIM_EGR_UG;
    TIM2->CR1 = TIM_CR1_CEN;
}

/* ---- the five data lanes ------------------------------------------------------------------
   lane 0 SAI1 A (the master: it makes the bit clock and frame sync), 1 SAI1 B, 2 SAI2 B,
   3 SAI2 A, 4 SAI3 A -- the rest take SAI1's clocks inside the chip. */
static SAI_HandleTypeDef sai[LANES];
static DMA_HandleTypeDef dma[LANES];
static int16_t buf[LANES][2 * HALF] __attribute__((aligned(32)));
static volatile uint32_t halves;          /* half-buffers lane 0 has finished */
static uint8_t fs_early = 1, falling = 1;

static int sai_setup(void)
{
    static SAI_Block_TypeDef *const blk[LANES] = { SAI1_Block_A, SAI1_Block_B, SAI2_Block_B, SAI2_Block_A, SAI3_Block_A };
    static DMA_Stream_TypeDef *const str[LANES] = { DMA1_Stream0, DMA1_Stream1, DMA1_Stream2, DMA1_Stream3, DMA1_Stream4 };
    static const uint32_t req[LANES] = { DMA_REQUEST_SAI1_A, DMA_REQUEST_SAI1_B, DMA_REQUEST_SAI2_B, DMA_REQUEST_SAI2_A, DMA_REQUEST_SAI3_A };
    __HAL_RCC_SAI1_CLK_ENABLE(); __HAL_RCC_SAI2_CLK_ENABLE(); __HAL_RCC_SAI3_CLK_ENABLE();
    __HAL_RCC_DMA1_CLK_ENABLE();
    for (int k = 0; k < LANES; k++) {
        SAI_HandleTypeDef *h = &sai[k];
        memset(h, 0, sizeof *h);
        h->Instance = blk[k];
        h->Init.AudioMode = k == 0 ? SAI_MODEMASTER_RX : SAI_MODESLAVE_RX;
        h->Init.Synchro = k == 0 ? SAI_ASYNCHRONOUS : k == 1 ? SAI_SYNCHRONOUS : SAI_SYNCHRONOUS_EXT_SAI1;
        h->Init.SynchroExt = k == 0 ? SAI_SYNCEXT_OUTBLOCKA_ENABLE : SAI_SYNCEXT_DISABLE;
        h->Init.OutputDrive = SAI_OUTPUTDRIVE_DISABLE;
        h->Init.NoDivider = SAI_MASTERDIVIDER_DISABLE;
        h->Init.FIFOThreshold = SAI_FIFOTHRESHOLD_1QF;
        h->Init.AudioFrequency = SAI_AUDIO_FREQUENCY_MCKDIV;
        h->Init.Mckdiv = 4;               /* 49.152 MHz / 4 = 12.288 MHz = 64 x 192 kHz */
        h->Init.MckOverSampling = SAI_MCK_OVERSAMPLING_DISABLE;
        h->Init.MonoStereoMode = SAI_STEREOMODE;
        h->Init.CompandingMode = SAI_NOCOMPANDING;
        h->Init.TriState = SAI_OUTPUT_NOTRELEASED;
        h->Init.Protocol = SAI_FREE_PROTOCOL;
        h->Init.DataSize = SAI_DATASIZE_16;
        h->Init.FirstBit = SAI_FIRSTBIT_MSB;
        h->Init.ClockStrobing = falling ? SAI_CLOCKSTROBING_FALLINGEDGE : SAI_CLOCKSTROBING_RISINGEDGE;
        h->FrameInit.FrameLength = 16 * SLOTS;
        h->FrameInit.ActiveFrameLength = 16 * SLOTS / 2;
        h->FrameInit.FSDefinition = SAI_FS_STARTFRAME;
        h->FrameInit.FSPolarity = SAI_FS_ACTIVE_HIGH;
        h->FrameInit.FSOffset = fs_early ? SAI_FS_BEFOREFIRSTBIT : SAI_FS_FIRSTBIT;
        h->SlotInit.FirstBitOffset = 0;
        h->SlotInit.SlotSize = SAI_SLOTSIZE_DATASIZE;
        h->SlotInit.SlotNumber = SLOTS;
        h->SlotInit.SlotActive = 0x0F;
        HAL_SAI_DeInit(h);
        if (HAL_SAI_Init(h) != HAL_OK) return -1;
        DMA_HandleTypeDef *d = &dma[k];
        memset(d, 0, sizeof *d);
        d->Instance = str[k];
        d->Init.Request = req[k];
        d->Init.Direction = DMA_PERIPH_TO_MEMORY;
        d->Init.PeriphInc = DMA_PINC_DISABLE;
        d->Init.MemInc = DMA_MINC_ENABLE;
        d->Init.PeriphDataAlignment = DMA_PDATAALIGN_HALFWORD;
        d->Init.MemDataAlignment = DMA_MDATAALIGN_HALFWORD;
        d->Init.Mode = DMA_CIRCULAR;
        d->Init.Priority = DMA_PRIORITY_HIGH;
        d->Init.FIFOMode = DMA_FIFOMODE_DISABLE;
        HAL_DMA_DeInit(d);
        if (HAL_DMA_Init(d) != HAL_OK) return -1;
        __HAL_LINKDMA(h, hdmarx, *d);
    }
    halves = 0;
    HAL_NVIC_SetPriority(DMA1_Stream0_IRQn, 1, 0);
    HAL_NVIC_EnableIRQ(DMA1_Stream0_IRQn);
    /* the followers first: they wait for the master's clocks, so all five start on one frame */
    for (int k = LANES - 1; k >= 0; k--)
        if (HAL_SAI_Receive_DMA(&sai[k], (uint8_t *)buf[k], 2 * HALF) != HAL_OK) return -1;
    return 0;
}

void DMA1_Stream0_IRQHandler(void) { HAL_DMA_IRQHandler(&dma[0]); }
void HAL_SAI_RxHalfCpltCallback(SAI_HandleTypeDef *h) { if (h == &sai[0]) halves++; }
void HAL_SAI_RxCpltCallback(SAI_HandleTypeDef *h) { if (h == &sai[0]) halves++; }

static uint64_t samples_now(void)
{
    uint32_t h, left;
    do { h = halves; left = __HAL_DMA_GET_COUNTER(&dma[0]); } while (h != halves);
    uint32_t in_buf = (2 * HALF - left) / SLOTS;                /* frames into the double buffer */
    uint32_t second = in_buf >= FRAMES;
    if (second != (h & 1)) h++;           /* the DMA is into the next half, its interrupt not yet taken */
    return (uint64_t)h * FRAMES + (second ? in_buf - FRAMES : in_buf);
}

/* ---- USB ------------------------------------------------------------------------------- */
void OTG_HS_IRQHandler(void) { tud_int_handler(1); }
void _init(void) { }                      /* the C library's start-up calls it; nothing to do */

size_t board_get_unique_id(uint8_t id[], size_t max_len)
{   /* the serial number the descriptors report: the chip's own 96-bit id */
    size_t n = max_len < 12 ? max_len : 12;
    memcpy(id, (const void *)UID_BASE, n);
    return n;
}
uint32_t tusb_time_millis_api(void) { return HAL_GetTick(); }

static int usb_setup(void)
{
    __HAL_RCC_USB1_OTG_HS_ULPI_CLK_ENABLE();
    __HAL_RCC_USB1_OTG_HS_CLK_ENABLE();
    HAL_PWREx_EnableUSBVoltageDetector();
    /* With the PHY, its oscillator or one ULPI line dead, the core's reset never completes
       and the USB stack would wait for it for ever: try it here first, with a time limit. */
    USB1_OTG_HS->GUSBCFG &= ~USB_OTG_GUSBCFG_PHYSEL;
    uint32_t t0 = HAL_GetTick();
    while (!(USB1_OTG_HS->GRSTCTL & USB_OTG_GRSTCTL_AHBIDL))
        if (HAL_GetTick() - t0 > 100) return -1;
    USB1_OTG_HS->GRSTCTL |= USB_OTG_GRSTCTL_CSRST;
    while (USB1_OTG_HS->GRSTCTL & USB_OTG_GRSTCTL_CSRST)
        if (HAL_GetTick() - t0 > 200) return -1;
    tud_configure_dwc2_t cfg = CFG_TUD_CONFIGURE_DWC2_DEFAULT;
    cfg.vbus_sensing = false;             /* VBUS is not wired to the core */
    tud_configure(1, TUD_CFGID_DWC2, &cfg);
    tusb_rhport_init_t init = { .role = TUSB_ROLE_DEVICE, .speed = TUSB_SPEED_AUTO };
    return tusb_init(1, &init) ? 0 : -1;
}

static void say(const char *s)
{
    tud_cdc_n_write_str(0, s);
    tud_cdc_n_write_flush(0);
}

static char *w_dec(char *p, uint64_t v)
{
    char t[20]; int n = 0;
    do { t[n++] = (char)('0' + v % 10); v /= 10; } while (v);
    while (n) *p++ = t[--n];
    return p;
}

static const char *r_num(const char *s, uint32_t *v, int base)
{
    while (*s == ' ') s++;
    const char *b = s; uint32_t x = 0;
    for (;; s++) {
        int d = (*s >= '0' && *s <= '9') ? *s - '0'
              : (base == 16 && (*s | 32) >= 'a' && (*s | 32) <= 'f') ? (*s | 32) - 'a' + 10 : -1;
        if (d < 0) break;
        x = x * (uint32_t)base + (uint32_t)d;
    }
    if (s == b) return 0;
    *v = x; return s;
}

static uint8_t mask;                      /* converters being sent */
static uint32_t sent_halves;              /* blocks dealt with so far */
static uint8_t dropped;

static void restart(void)
{
    emit(emit_on);
    if (sai_setup() < 0) say("E sai\n");
    sent_halves = 0; dropped = 0;
}

static void line(const char *s)
{
    char l[80], *p; uint32_t a, b, c;
    switch (*s) {
    case '?':
        say("I psg-optical-bench 1 fs=192000 block=960 slots=4\n"); return;
    case 'T':
        p = l; *p++ = 'T'; *p++ = ' '; p = w_dec(p, samples_now()); *p++ = '\n'; *p = 0;
        say(l); return;
    case 'L':
        if (r_num(s + 1, &a, 10) && a < (1u << LANES)) { mask = (uint8_t)a; sent_halves = halves; say("OK L\n"); return; }
        break;
    case 'E':
        if (r_num(s + 1, &a, 10)) { emit_on = a != 0; TIM2->CCR2 = a ? 2048 : 0; say("OK E\n"); return; }
        break;
    case 'W':
        if ((s = r_num(s + 1, &a, 16)) && (s = r_num(s, &b, 16)) && r_num(s, &c, 16)) {
            int bad = i2c_write(0x00, (uint8_t)a) | i2c_write((uint8_t)b, (uint8_t)c) | i2c_write(0x00, 0x00);
            say(bad ? "E no answer\n" : "OK W\n"); return;
        }
        break;
    case 'R':
        say(adc_setup() ? "E no answer\n" : "OK R\n"); return;
    case 'F':
        if ((s = r_num(s + 1, &a, 10)) && r_num(s, &b, 10)) {
            fs_early = a != 0; falling = b != 0; restart(); say("OK F\n"); return;
        }
        break;
    case 0: return;
    }
    say("E line\n");
}

static void control_pump(void)
{
    static char ln[64]; static uint8_t n;
    while (tud_cdc_n_available(0)) {
        char ch = (char)tud_cdc_n_read_char(0);
        if (ch == '\r') continue;
        if (ch == '\n') { ln[n] = 0; line(ln); n = 0; }
        else if (n < sizeof ln - 1) ln[n++] = ch;
    }
}

static void stream_pump(void)
{
    while (sent_halves != halves) {
        if (halves - sent_halves > 1) {   /* the next half is already being written over */
            sent_halves = halves - 1; dropped = 1;
        }
        uint32_t h = sent_halves;
        if (mask && tud_cdc_n_connected(1)) {
            uint32_t need = 16;
            for (int k = 0; k < LANES; k++) if (mask & (1u << k)) need += HALF * 2;
            if (tud_cdc_n_write_available(1) < need) return;        /* later; or it is dropped */
            uint8_t hd[16] = { 'P', 'S', 'G', 'O', mask, dropped, (uint8_t)FRAMES, (uint8_t)(FRAMES >> 8) };
            uint64_t first = (uint64_t)h * FRAMES;
            memcpy(hd + 8, &first, 8);
            tud_cdc_n_write(1, hd, 16);
            for (int k = 0; k < LANES; k++)
                if (mask & (1u << k)) tud_cdc_n_write(1, &buf[k][(h & 1) * HALF], HALF * 2);
            tud_cdc_n_write_flush(1);
            dropped = 0;
        }
        sent_halves = h + 1;
    }
}

int main(void)
{
    HAL_Init();
    int clk = clock_setup();
    pins_setup();
    dbg_setup();
    dbg(clk ? "psg-optical-bench: CLOCK FAILED\r\n" : "psg-optical-bench: clock ok\r\n");
    HAL_Delay(2000);                      /* a window for the debugger before anything else */
    int adc = adc_setup();
    dbg(adc ? "converters: NO ANSWER on I2C\r\n" : "converters: configured\r\n");
    emit(1);
    int s = sai_setup();
    dbg(s ? "SAI: FAILED\r\n" : "SAI: running\r\n");
    int u = usb_setup();
    dbg(u ? "USB: core did not start (PHY, its clock, or a ULPI line)\r\n" : "USB: started\r\n");
    while (u) { }                         /* nothing to talk to; TP12 has said why */
    uint8_t told = 0;
    while (1) {
        tud_task();
        if (!told && tud_cdc_n_connected(0)) {
            told = 1;
            if (adc) say("E converters: no answer on I2C\n");
            if (s) say("E sai\n");
        }
        control_pump();
        stream_pump();
    }
}
