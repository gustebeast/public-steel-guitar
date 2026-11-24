/* QT Py CH32V203 bench firmware: one TMC2209 on a SilentStepStick, driven open loop, commanded
 * from the Pi over USB-CDC (bench/OPENLOOP_BENCH.md, README.md beside this file).
 *
 * Pads (Adafruit's QT Py CH32V203 pinout page):
 *   MI  PA6  TIM3_CH1  -> STEP   compare-toggle: one edge per step, the driver in dedge mode
 *   MO  PA7            -> DIR
 *   SCK PA5            -> ENN    high = outputs off; set high before anything else
 *   TX  PA2  USART2_TX -> 1k -> PDN_UART   (TMC2209 datasheet p17, Fig 4.1)
 *   RX  PA3  USART2_RX -> PDN_UART direct  (so every byte sent is also heard: skipped)
 * All default mappings; nothing here writes AFIO_PCFR1 (README.md "Pin map", with the pages):
 *   CH32V203 datasheet V3.0, Table 3-1-3 (QFN28/G6, PDF p23): pin 8 PA2 USART2_TX, pin 9 PA3
 *   USART2_RX, pin 12 PA6 TIM3_CH1, under "default alternate function"; PA2/3/5/6/7 each have
 *   their own package pin.
 *   CH32FV2x_V3xRM V2.5: AFIO_PCFR1 resets to 0x00000000 (p148), TIM3_RM 00 = CH1 on PA6 (p153,
 *   Table 10-17 p136), USART2_RM 0 = TX PA2, RX PA3 (p154, Table 10-24 p138); compare outputs
 *   and USART TX as alternate push-pull, RX floating or pull-up (Tables 10-2, 10-3, p133).
 * The edges come from the timer's compare output, never from code, so their timing does not
 * depend on interrupt latency; MicroPlyer needs a jitter-free STEP (datasheet 13.3). The ISR only
 * loads the next compare, which has at least AXIS_CMIN ticks (5 us) to arrive.
 */
#include <string.h>

#include "ch32v20x.h"
#include "tusb.h"

#include "bench.h"
#include "tmc.h"

#define RSENSE_MOHM 110     /* the SilentStepStick's sense resistors */
#define TMC_ADDR    0       /* MS1, MS2 to GND */
#define UART_BAUD   115200
#define UART_MS     10      /* a reply is 8 bytes plus the 8-bit-time send delay: ~1 ms */

#define PIN_ENN  GPIO_Pin_5
#define PIN_STEP GPIO_Pin_6
#define PIN_DIR  GPIO_Pin_7

static bench_t B;
static volatile uint32_t ms_ticks;

/* ── time ── */
__attribute__((used)) void systick_isr(void)
{
    SysTick->SR = 0;
    ms_ticks++;
}

uint32_t tusb_time_millis_api(void)
{
    return ms_ticks;
}

/* ── USB: the USBD raises three lines that all go to TinyUSB's one handler. They share one
 * priority so none preempts another; naked, so the hardware stack (HWSTK) saves the context,
 * as TinyUSB's own ch32v20x board file does. ── */
#define FSDEV_ISR(name) \
    __attribute__((naked)) __attribute__((used)) void name(void) \
    { __asm volatile("li a0, 0\n\t call dcd_int_handler\n\t mret"); }
FSDEV_ISR(USB_LP_CAN1_RX0_IRQHandler)
FSDEV_ISR(USB_HP_CAN1_TX_IRQHandler)
FSDEV_ISR(USBWakeUp_IRQHandler)

/* ── STEP ── */
static void step_off(void)
{
    TIM3->DMAINTENR &= (uint16_t)~TIM_IT_CC1;
    TIM3->CHCTLR1 = (uint16_t)((TIM3->CHCTLR1 & ~TIM_OC1M) | TIM_OCMode_Timing);  /* level held */
}

/* The step ISR preempts USB (TIM3 priority 0x00, the rest 0x80; set in main) so a USB packet
 * never makes it miss a compare: past 1/4 step at 1600 rpm the edges are 23 us apart. Nesting is
 * only safe with naked handlers on the hardware stack (TinyUSB's ch32v20x board file explains),
 * so every handler here is naked and calls a plain function. */
#define NAKED_ISR(name, fn) \
    __attribute__((naked)) __attribute__((used)) void name(void) \
    { __asm volatile("call " #fn "\n\t mret"); }

__attribute__((used)) void tim3_isr(void)
{
    if (TIM3->INTFR & TIM_FLAG_CC1) {
        TIM3->INTFR = (uint16_t)~TIM_FLAG_CC1;
        uint32_t t = bench_step_isr(&B);
        if (t)
            TIM3->CH1CVR = (uint16_t)(TIM3->CH1CVR + t);
        else
            step_off();
    }
}

NAKED_ISR(TIM3_IRQHandler, tim3_isr)
NAKED_ISR(SysTick_Handler, systick_isr)

static void op_step_start(void *ctx, int dir, uint32_t first)
{
    (void)ctx;
    GPIO_WriteBit(GPIOA, PIN_DIR, dir > 0 ? Bit_SET : Bit_RESET);  /* DIR setup is 20 ns (p75) */
    if (first < AXIS_CMIN)
        first = AXIS_CMIN;
    TIM3->CH1CVR = (uint16_t)(TIM3->CNT + first);
    TIM3->INTFR = (uint16_t)~TIM_FLAG_CC1;
    TIM3->CHCTLR1 = (uint16_t)((TIM3->CHCTLR1 & ~TIM_OC1M) | TIM_OCMode_Toggle);
    TIM3->DMAINTENR |= TIM_IT_CC1;
}

static void op_step_stop(void *ctx)
{
    (void)ctx;
    step_off();
}

static void op_lock(void *ctx)
{
    (void)ctx;
    NVIC_DisableIRQ(TIM3_IRQn);
}

static void op_unlock(void *ctx)
{
    (void)ctx;
    NVIC_EnableIRQ(TIM3_IRQn);
}

static void op_enable(void *ctx, int on)
{
    (void)ctx;
    GPIO_WriteBit(GPIOA, PIN_ENN, on ? Bit_RESET : Bit_SET);
}

/* ── the driver's UART: TX and RX share the one wire, so each byte sent comes back first ── */
static int uart_xfer(const uint8_t *tx, int ntx, uint8_t *rx, int nrx)
{
    while (USART2->STATR & (USART_FLAG_RXNE | USART_FLAG_ORE))
        (void)USART2->DATAR;
    for (int i = 0; i < ntx; i++) {
        while (!(USART2->STATR & USART_FLAG_TXE))
            ;
        USART2->DATAR = tx[i];
    }
    int got = 0, need = ntx + nrx;
    uint32_t t0 = ms_ticks;
    while (got < need) {
        if (USART2->STATR & USART_FLAG_RXNE) {
            uint8_t b = (uint8_t)USART2->DATAR;
            if (got >= ntx)
                rx[got - ntx] = b;
            got++;
        } else if (ms_ticks - t0 > UART_MS) {
            return got < ntx ? -10 : -11;   /* -10: our own bytes never came back (wiring) */
        }
    }
    return 0;
}

static int op_tmc_write(void *ctx, uint8_t reg, uint32_t v)
{
    (void)ctx;
    uint8_t dg[8];
    tmc_write_dg(dg, TMC_ADDR, reg, v);
    return uart_xfer(dg, 8, NULL, 0);
}

static int op_tmc_read(void *ctx, uint8_t reg, uint32_t *v)
{
    (void)ctx;
    uint8_t dg[4], rep[8];
    tmc_read_dg(dg, TMC_ADDR, reg);
    int e = uart_xfer(dg, 4, rep, 8);
    return e ? e : tmc_parse_reply(rep, reg, v);
}

/* ── set-up ── */
static void gpio_init(void)
{
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_AFIO, ENABLE);
    GPIO_SetBits(GPIOA, PIN_ENN);                       /* "Start with ENN=high!" (p12) */
    GPIO_InitTypeDef g = {.GPIO_Speed = GPIO_Speed_50MHz};
    g.GPIO_Pin = PIN_ENN | PIN_DIR;
    g.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_Init(GPIOA, &g);
    g.GPIO_Pin = PIN_STEP | GPIO_Pin_2;                 /* TIM3_CH1, USART2_TX */
    g.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_Init(GPIOA, &g);
    g.GPIO_Pin = GPIO_Pin_3;                            /* USART2_RX */
    g.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_Init(GPIOA, &g);
}

static void uart_init(void)
{
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_USART2, ENABLE);
    USART_InitTypeDef u = {
        .USART_BaudRate = UART_BAUD,
        .USART_WordLength = USART_WordLength_8b,
        .USART_StopBits = USART_StopBits_1,
        .USART_Parity = USART_Parity_No,
        .USART_Mode = USART_Mode_Tx | USART_Mode_Rx,
        .USART_HardwareFlowControl = USART_HardwareFlowControl_None,
    };
    USART_Init(USART2, &u);
    USART_Cmd(USART2, ENABLE);
}

/* TIM3 free-runs at AXIS_TICK_HZ; channel 1 toggles STEP at each compare while a move runs */
static void tim_init(void)
{
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM3, ENABLE);
    RCC_ClocksTypeDef c;
    RCC_GetClocksFreq(&c);
    /* timers on APB1 run at twice PCLK1 when APB1 is divided */
    uint32_t tclk = c.PCLK1_Frequency * (c.PCLK1_Frequency == c.HCLK_Frequency ? 1 : 2);
    TIM_TimeBaseInitTypeDef tb = {
        .TIM_Prescaler = (uint16_t)(tclk / AXIS_TICK_HZ - 1),
        .TIM_CounterMode = TIM_CounterMode_Up,
        .TIM_Period = 0xFFFF,
        .TIM_ClockDivision = TIM_CKD_DIV1,
    };
    TIM_TimeBaseInit(TIM3, &tb);
    TIM_OCInitTypeDef oc = {
        .TIM_OCMode = TIM_OCMode_Timing,
        .TIM_OutputState = TIM_OutputState_Enable,
        .TIM_Pulse = 0,
        .TIM_OCPolarity = TIM_OCPolarity_High,
    };
    TIM_OC1Init(TIM3, &oc);
    TIM_OC1PreloadConfig(TIM3, TIM_OCPreload_Disable);  /* a new compare takes effect at once */
    TIM_Cmd(TIM3, ENABLE);
    NVIC_EnableIRQ(TIM3_IRQn);
}

static void tick_init(void)
{
    SysTick->CTLR = 0;
    SysTick->SR = 0;
    SysTick->CNT = 0;
    SysTick->CMP = SystemCoreClock / 1000 - 1;
    SysTick->CTLR = 0xF;                                /* on, interrupt, HCLK, auto-reload */
    NVIC_EnableIRQ(SysTicK_IRQn);
}

static void usb_init(void)
{
    /* 48 MHz for the USB from the 96 MHz PLL */
    RCC_USBCLKConfig(RCC_USBCLKSource_PLLCLK_Div2);
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_USB, ENABLE);
    const tusb_rhport_init_t init = {.role = TUSB_ROLE_DEVICE, .speed = TUSB_SPEED_AUTO};
    tusb_init(BOARD_TUD_RHPORT, &init);
}

/* ── the command line ── */
static void serve(void)
{
    static char line[96];
    static int len;
    static char out[160];
    while (tud_cdc_available()) {
        int ch = tud_cdc_read_char();
        if (ch < 0)
            break;
        if (ch == '\r' || ch == '\n') {
            if (len == 0)
                continue;
            line[len] = 0;
            int n = bench_line(&B, line, out, sizeof out - 2);
            if (n > (int)sizeof out - 3)
                n = sizeof out - 3;
            out[n++] = '\n';
            tud_cdc_write(out, (uint32_t)n);
            tud_cdc_write_flush();
            len = 0;
        } else if (len < (int)sizeof line - 1) {
            line[len++] = (char)ch;
        } else {
            len = 0;                                    /* an overlong line is dropped whole */
        }
    }
}

int main(void)
{
    SystemCoreClockUpdate();
    gpio_init();
    tick_init();
    uart_init();
    static const bench_ops_t ops = {
        .enable = op_enable, .tmc_read = op_tmc_read, .tmc_write = op_tmc_write,
        .step_start = op_step_start, .step_stop = op_step_stop,
        .lock = op_lock, .unlock = op_unlock, .ctx = NULL,
    };
    bench_init(&B, &ops, RSENSE_MOHM);
    tim_init();
    usb_init();
    NVIC_SetPriority(TIM3_IRQn, 0x00);
    NVIC_SetPriority(SysTicK_IRQn, 0x80);
    NVIC_SetPriority(USB_LP_CAN1_RX0_IRQn, 0x80);
    NVIC_SetPriority(USB_HP_CAN1_TX_IRQn, 0x80);
    NVIC_SetPriority(USBWakeUp_IRQn, 0x80);
    for (;;) {
        tud_task();
        serve();
    }
}
