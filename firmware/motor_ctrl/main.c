/* motor_ctrl BENCH firmware: a timestamped USB <-> CAN scheduler.
 *
 * The board (CH32V307WCU6, 8 MHz crystal) shows up on its USB as a serial port. The host
 * sends CAN frames to transmit, either now or at a time on THIS board's microsecond clock,
 * and gets every received frame back with the time it arrived. Nothing here knows what a
 * SERVO42D is: the motor protocol lives on the host (bench/psgbench/servo.py), where it is
 * a text edit to correct once a real motor answers.
 *
 *   bus 0 = bus A, CAN1 remapped to PB8 (RX) / PB9 (TX)  -- the motors
 *   bus 1 = bus B, CAN2 on PB12 (RX) / PB13 (TX)         -- the lever sensors
 *
 * Lines from the host (ASCII, '\n'; ids and data in hex, the rest decimal):
 *   ?                         -> I psg-motor-bench <version> <t_us>
 *   T                         -> T <t_us>
 *   B <bus> <bit/s>           -> OK B ...      set a bus's bit rate (default 500000)
 *   S <bus> <id> <data>       send now (as sequence 0)
 *   Q <seq> <t_us> <bus> <id> <data>   send at t_us; lines must arrive in time order
 *   C                         -> OK C          drop everything queued
 * Lines to the host:
 *   R <bus> <t_us> <id> <data>     a frame received
 *   X <seq> <bus> <t_us>           a frame handed to the controller
 *   D <seq> <bus> <t_us> <ok>      ...and when it had left the pin (ok 1) or failed (0)
 *   E <what>                       a line refused, or the queue full
 *   L <count>                      output lost because the host was not reading
 *
 * NOT YET RUN ON A BOARD (2026-10-13): it compiles, and that is all that is known.
 */
#include <string.h>
#include "ch32v30x.h"
#include "ch32v30x_usbfs_device.h"
#include "UART.h"

#define VERSION 1

/* ---- the clock: SysTick free-running on HCLK, 64 bits ------------------------------- */
static uint32_t ticks_per_us;

static uint64_t now_us(void)
{
    uint32_t hi, lo, *p = (uint32_t *)&SysTick->CNT;
    do { hi = p[1]; lo = p[0]; } while (hi != p[1]);
    return (((uint64_t)hi << 32) | lo) / ticks_per_us;
}

void Delay_Us(uint32_t n)           /* the USB driver wants one; debug.c's would stop the clock */
{
    uint64_t end = now_us() + n;
    while (now_us() < end) { }
}

/* ---- USB serial, on WCH's own CDC device code (their UART bridge's variables) -------- */
volatile UART_CTL Uart;
volatile uint32_t UARTx_Rx_DMACurCount, UARTx_Rx_DMALastCount;
__attribute__((aligned(4))) uint8_t UART2_Tx_Buf[DEF_UARTx_TX_BUF_LEN];   /* host -> us */

void UART2_USB_Init(void) { }       /* the host set a baud rate: there is no UART behind this */

void UART2_ParaInit(uint8_t mode)
{
    memset((void *)&Uart, 0, sizeof Uart);
    if (mode) {
        Uart.Com_Cfg[0] = (uint8_t)115200; Uart.Com_Cfg[1] = (uint8_t)(115200 >> 8);
        Uart.Com_Cfg[2] = (uint8_t)(115200 >> 16); Uart.Com_Cfg[6] = 8;
    }
}

static uint8_t out_buf[8192];       /* us -> host */
static volatile uint16_t out_head, out_tail;
static uint32_t out_lost;
static uint8_t out_zlp;

static void out_put(const char *s, uint16_t n)
{
    __disable_irq();                /* the CAN interrupts write here too */
    uint16_t used = (uint16_t)(out_head - out_tail) % sizeof out_buf;
    if (n >= sizeof out_buf - used) { out_lost += n; __enable_irq(); return; }
    for (uint16_t i = 0; i < n; i++) {
        out_buf[out_head] = (uint8_t)s[i];
        out_head = (out_head + 1) % sizeof out_buf;
    }
    __enable_irq();
}

static void out_pump(void)
{
    static uint8_t pkt[DEF_USBD_FS_PACK_SIZE];
    if (!USBFS_DevEnumStatus || USBFS_Endp_Busy[DEF_UEP3]) return;
    uint16_t n = 0;
    __disable_irq();
    while (n < sizeof pkt && out_tail != out_head) {
        pkt[n++] = out_buf[out_tail];
        out_tail = (out_tail + 1) % sizeof out_buf;
    }
    __enable_irq();
    if (n == 0 && !out_zlp) return;
    NVIC_DisableIRQ(USBFS_IRQn);
    USBFS_Endp_DataUp(DEF_UEP3, pkt, n, DEF_UEP_CPY_LOAD);
    NVIC_EnableIRQ(USBFS_IRQn);
    out_zlp = (n == sizeof pkt);    /* a full packet needs a short one after it */
}

/* one packet from the host, or -1 */
static int in_take(uint8_t *dst)
{
    if (!Uart.Tx_RemainNum) return -1;
    int n = Uart.Tx_PackLen[Uart.Tx_DealNum];
    memcpy(dst, &UART2_Tx_Buf[Uart.Tx_DealNum * DEF_USB_FS_PACK_LEN], n);
    NVIC_DisableIRQ(USBFS_IRQn);
    Uart.Tx_PackLen[Uart.Tx_DealNum] = 0;
    if (++Uart.Tx_DealNum >= DEF_UARTx_TX_BUF_NUM_MAX) Uart.Tx_DealNum = 0;
    Uart.Tx_RemainNum--;
    if (Uart.USB_Down_StopFlag && Uart.Tx_RemainNum < 2) {
        USBFSD->UEP2_RX_CTRL &= ~USBFS_UEP_R_RES_MASK;
        USBFSD->UEP2_RX_CTRL |= USBFS_UEP_R_RES_ACK;
        Uart.USB_Down_StopFlag = 0;
    }
    NVIC_EnableIRQ(USBFS_IRQn);
    return n;
}

/* ---- writing lines ---------------------------------------------------------------------- */
static char *w_dec(char *p, uint64_t v)
{
    char t[20]; int n = 0;
    do { t[n++] = (char)('0' + v % 10); v /= 10; } while (v);
    while (n) *p++ = t[--n];
    return p;
}

static char *w_hex(char *p, uint32_t v, int digits)
{
    for (int i = digits - 1; i >= 0; i--) *p++ = "0123456789ABCDEF"[(v >> (4 * i)) & 15];
    return p;
}

static void say(const char *s) { out_put(s, (uint16_t)strlen(s)); }

static void say_ev(char tag, uint32_t a, int b, uint64_t t, int tail)
{   /* "<tag> <a> <b> <t>[ <tail>]\n" */
    char l[64], *p = l;
    *p++ = tag; *p++ = ' '; p = w_dec(p, a); *p++ = ' '; p = w_dec(p, (uint64_t)b);
    *p++ = ' '; p = w_dec(p, t);
    if (tail >= 0) { *p++ = ' '; p = w_dec(p, (uint64_t)tail); }
    *p++ = '\n';
    out_put(l, (uint16_t)(p - l));
}

/* ---- CAN -------------------------------------------------------------------------------- */
static CAN_TypeDef *const BUS[2] = { CAN1, CAN2 };
static volatile uint8_t  flying[2];         /* a frame is in the controller */
static volatile uint32_t flying_seq[2];

static int can_rate(int bus, uint32_t bps)
{
    RCC_ClocksTypeDef ck;
    RCC_GetClocksFreq(&ck);
    uint32_t div = ck.PCLK1_Frequency / (16 * bps);         /* 16 quanta: 1 + 13 + 2, 87.5 % */
    if (bps == 0 || div == 0 || div > 1024 || div * 16 * bps != ck.PCLK1_Frequency) return -1;
    CAN_InitTypeDef c = {0};
    c.CAN_Prescaler = (uint16_t)div;
    c.CAN_Mode = CAN_Mode_Normal;
    c.CAN_SJW = CAN_SJW_1tq; c.CAN_BS1 = CAN_BS1_13tq; c.CAN_BS2 = CAN_BS2_2tq;
    c.CAN_ABOM = ENABLE;            /* come back from bus-off by itself */
    c.CAN_NART = DISABLE;           /* retry until acknowledged */
    c.CAN_TXFP = ENABLE;
    CAN_DeInit(BUS[bus]);
    if (CAN_Init(BUS[bus], &c) != CAN_InitStatus_Success) return -1;
    CAN_FilterInitTypeDef f = {0};  /* take everything; CAN2's banks start at 14 */
    f.CAN_FilterNumber = bus ? 14 : 0;
    f.CAN_FilterMode = CAN_FilterMode_IdMask;
    f.CAN_FilterScale = CAN_FilterScale_32bit;
    f.CAN_FilterFIFOAssignment = CAN_Filter_FIFO0;
    f.CAN_FilterActivation = ENABLE;
    CAN_SlaveStartBank(14);
    CAN_FilterInit(&f);
    CAN_ITConfig(BUS[bus], CAN_IT_FMP0 | CAN_IT_TME, ENABLE);
    flying[bus] = 0;
    return 0;
}

static void can_setup(void)
{
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_AFIO | RCC_APB2Periph_GPIOB, ENABLE);
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_CAN1 | RCC_APB1Periph_CAN2, ENABLE);
    GPIO_PinRemapConfig(GPIO_Remap1_CAN1, ENABLE);          /* CAN1 on PB8 / PB9 */
    GPIO_InitTypeDef g = {0};
    g.GPIO_Speed = GPIO_Speed_50MHz;
    g.GPIO_Pin = GPIO_Pin_9 | GPIO_Pin_13; g.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_Init(GPIOB, &g);
    g.GPIO_Pin = GPIO_Pin_8 | GPIO_Pin_12; g.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_Init(GPIOB, &g);
    can_rate(0, 500000);
    can_rate(1, 500000);
    NVIC_EnableIRQ(USB_LP_CAN1_RX0_IRQn); NVIC_EnableIRQ(USB_HP_CAN1_TX_IRQn);
    NVIC_EnableIRQ(CAN2_RX0_IRQn);        NVIC_EnableIRQ(CAN2_TX_IRQn);
}

static void rx_irq(int bus)
{
    CanRxMsg m;
    while (CAN_MessagePending(BUS[bus], CAN_FIFO0)) {
        uint64_t t = now_us();
        CAN_Receive(BUS[bus], CAN_FIFO0, &m);
        char l[64], *p = l;
        *p++ = 'R'; *p++ = ' '; *p++ = (char)('0' + bus); *p++ = ' '; p = w_dec(p, t); *p++ = ' ';
        p = (m.IDE == CAN_Id_Extended) ? w_hex(p, m.ExtId, 8) : w_hex(p, m.StdId, 3);
        *p++ = ' ';
        for (int i = 0; i < m.DLC && i < 8; i++) p = w_hex(p, m.Data[i], 2);
        *p++ = '\n';
        out_put(l, (uint16_t)(p - l));
    }
}

static void tx_irq(int bus)
{
    uint64_t t = now_us();
    uint32_t st = BUS[bus]->TSTATR;
    if (st & (CAN_TSTATR_RQCP0 | CAN_TSTATR_RQCP1 | CAN_TSTATR_RQCP2)) {
        int ok = (st & (CAN_TSTATR_TXOK0 | CAN_TSTATR_TXOK1 | CAN_TSTATR_TXOK2)) != 0;
        BUS[bus]->TSTATR = CAN_TSTATR_RQCP0 | CAN_TSTATR_RQCP1 | CAN_TSTATR_RQCP2;
        if (flying[bus]) { say_ev('D', flying_seq[bus], bus, t, ok); flying[bus] = 0; }
    }
}

void USB_LP_CAN1_RX0_IRQHandler(void) __attribute__((interrupt));
void USB_HP_CAN1_TX_IRQHandler(void) __attribute__((interrupt));
void CAN2_RX0_IRQHandler(void) __attribute__((interrupt));
void CAN2_TX_IRQHandler(void) __attribute__((interrupt));
void USB_LP_CAN1_RX0_IRQHandler(void) { rx_irq(0); }
void USB_HP_CAN1_TX_IRQHandler(void) { tx_irq(0); }
void CAN2_RX0_IRQHandler(void) { rx_irq(1); }
void CAN2_TX_IRQHandler(void) { tx_irq(1); }

/* ---- the queue: frames in the order the host gave them -------------------------------- */
typedef struct { uint64_t t; uint32_t seq, id; uint8_t bus, len, data[8]; } job_t;
#define NQ 512
static job_t q[NQ];
static uint16_t q_head, q_tail;

static int can_send(const job_t *j)
{
    CanTxMsg m = {0};
    if (j->id > 0x7FF) { m.ExtId = j->id; m.IDE = CAN_Id_Extended; }
    else               { m.StdId = j->id; m.IDE = CAN_Id_Standard; }
    m.RTR = CAN_RTR_Data; m.DLC = j->len;
    memcpy(m.Data, j->data, j->len);
    __disable_irq();
    flying_seq[j->bus] = j->seq; flying[j->bus] = 1;
    uint64_t t = now_us();
    uint8_t box = CAN_Transmit(BUS[j->bus], &m);
    if (box == CAN_TxStatus_NoMailBox) flying[j->bus] = 0;
    __enable_irq();
    if (box == CAN_TxStatus_NoMailBox) return -1;
    say_ev('X', j->seq, j->bus, t, -1);
    return 0;
}

static void q_run(void)
{   /* one frame in flight on a bus at a time, so they leave in order and D names its X */
    while (q_tail != q_head) {
        job_t *j = &q[q_tail];
        if (flying[j->bus] || now_us() < j->t) return;
        if (can_send(j) < 0) return;
        q_tail = (q_tail + 1) % NQ;
    }
}

/* ---- reading lines ---------------------------------------------------------------------- */
static const char *r_num(const char *s, uint64_t *v, int base)
{
    while (*s == ' ') s++;
    const char *b = s; uint64_t x = 0;
    for (;; s++) {
        int d = (*s >= '0' && *s <= '9') ? *s - '0'
              : (base == 16 && (*s | 32) >= 'a' && (*s | 32) <= 'f') ? (*s | 32) - 'a' + 10 : -1;
        if (d < 0) break;
        x = x * base + d;
    }
    if (s == b) return 0;
    *v = x; return s;
}

static const char *r_frame(const char *s, job_t *j)
{   /* "<bus> <id> <data>" */
    uint64_t v;
    if (!(s = r_num(s, &v, 10)) || v > 1) return 0;
    j->bus = (uint8_t)v;
    if (!(s = r_num(s, &v, 16)) || v > 0x1FFFFFFF) return 0;
    j->id = (uint32_t)v;
    while (*s == ' ') s++;
    int n = 0;
    while (s[0] && s[1] && n < 8) {
        uint64_t b; char two[3] = { s[0], s[1], 0 };
        if (!r_num(two, &b, 16)) return 0;
        j->data[n++] = (uint8_t)b; s += 2;
    }
    if (*s) return 0;
    j->len = (uint8_t)n;
    return s;
}

static void line(const char *s)
{
    uint64_t v; job_t j; char l[48], *p;
    switch (*s) {
    case '?':
        say("I psg-motor-bench "); p = w_dec(l, VERSION); *p++ = ' '; p = w_dec(p, now_us());
        *p++ = '\n'; out_put(l, (uint16_t)(p - l)); return;
    case 'T':
        p = l; *p++ = 'T'; *p++ = ' '; p = w_dec(p, now_us()); *p++ = '\n';
        out_put(l, (uint16_t)(p - l)); return;
    case 'C':
        q_tail = q_head; say("OK C\n"); return;
    case 'B': {
        uint64_t bus;
        if ((s = r_num(s + 1, &bus, 10)) && bus <= 1 && r_num(s, &v, 10)
                && can_rate((int)bus, (uint32_t)v) == 0) { say("OK B\n"); return; }
        break; }
    case 'S':
        j.seq = 0; j.t = 0;
        if (r_frame(s + 1, &j)) { if (can_send(&j) < 0) say("E busy\n"); return; }
        break;
    case 'Q':
        if ((s = r_num(s + 1, &v, 10))) {
            j.seq = (uint32_t)v;
            if ((s = r_num(s, &j.t, 10)) && r_frame(s, &j)) {
                uint16_t nx = (uint16_t)((q_head + 1) % NQ);
                if (nx == q_tail) { say("E full\n"); return; }
                q[q_head] = j; q_head = nx; return;
            }
        }
        break;
    case 0: return;
    }
    say("E line\n");
}

static void in_pump(void)
{
    static char ln[96]; static uint8_t n;
    uint8_t pkt[DEF_USBD_FS_PACK_SIZE];
    int got = in_take(pkt);
    for (int i = 0; i < got; i++) {
        char c = (char)pkt[i];
        if (c == '\r') continue;
        if (c == '\n') { ln[n] = 0; line(ln); n = 0; }
        else if (n < sizeof ln - 1) ln[n++] = c;
    }
}

void NMI_Handler(void) __attribute__((interrupt));
void HardFault_Handler(void) __attribute__((interrupt));
void NMI_Handler(void) { }
void HardFault_Handler(void) { NVIC_SystemReset(); while (1) { } }

int main(void)
{
    SystemCoreClockUpdate();
    ticks_per_us = SystemCoreClock / 1000000;
    SysTick->CTLR = 0; SysTick->CNT = 0; SysTick->CMP = ~0ULL;
    SysTick->CTLR = 0x5;            /* count HCLK, upward, no reload */
    UART2_ParaInit(1);
    can_setup();
    USBFS_RCC_Init();
    USBFS_Device_Init(ENABLE);
    uint32_t lost_said = 0;
    while (1) {
        q_run();
        in_pump();
        q_run();
        if (out_lost != lost_said && out_head == out_tail) {
            char l[24], *p = l; lost_said = out_lost;
            *p++ = 'L'; *p++ = ' '; p = w_dec(p, lost_said); *p++ = '\n';
            out_put(l, (uint16_t)(p - l));
        }
        out_pump();
    }
}
