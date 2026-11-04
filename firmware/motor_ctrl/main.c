/* motor_ctrl BENCH firmware: a timestamped USB <-> CAN scheduler.
 *
 * The board (CH32V307WCU6, 8 MHz crystal) shows up on its USB as a serial port (R1: the MCU's
 * own USB CDC; R2, make REV=2: U7's CH340C on USART1, every line inside a checked frame,
 * link_uart.c and frame.h). The host
 * sends CAN frames to transmit, either now or at a time on THIS board's microsecond clock,
 * and gets every received frame back with the time it arrived. Nothing here knows what a
 * SERVO42D is: the motor protocol lives on the host (bench/publicbench/servo.py), where it is
 * a text edit to correct once a real motor answers.
 *
 *   bus 0 = bus A, CAN1 remapped to PB8 (RX) / PB9 (TX)  -- the motors
 *   bus 1 = bus B, CAN2 on PB12 (RX) / PB13 (TX)         -- the lever sensors
 *
 * Lines from the host (ASCII, '\n'; ids and data in hex, the rest decimal):
 *   B                         back to the loader (../output_panel/boot.c)
 *   ?                         -> I public-steel-guitar-motor-bench <version> <t_us>
 *   T                         -> T <t_us>
 *   B <bus> <bit/s>           -> OK B ...      set a bus's bit rate (default 500000)
 *   S <bus> <id> <data>       send now (as sequence 0)
 *   Q <seq> <t_us> <bus> <id> <data>   send at t_us; lines must arrive in time order
 *   C                         -> OK C          drop everything queued
 *   V <bus>                   -> V <errors, from ERRSR> <mailboxes, TSTATR> <PCLK1 Hz>
 *                                errors bits 4-6 are the last error: 3 no ACK, 4/5 bit, 7 none yet;
 *                                bits 16-23 what we sent wrong, 24-31 what we received wrong
 *   F                         -> F <frames dropped>     R2 only: the link's own errors
 *   P                         -> P <table ok> <on> <F5 frames sent> <string states 0-3 x10> <table crc>
 *   P 0 / P 1                 -> OK P          stop / start driving the motors (not kept)
 *   P Z                       -> OK P          every motor's position is open pitch again
 *   P W <offset> <data>       -> OK P          into the table being loaded (play.h, 32 bytes a line)
 *   P S                       -> OK P S        check it, keep it in flash, play from it
 * Lines to the host:
 *   R <bus> <t_us> <id> <data>     a frame received
 *   X <seq> <bus> <t_us>           a frame handed to the controller
 *   D <seq> <bus> <t_us> <ok>      ...and when it had left the pin (ok 1) or failed (0)
 *   E <what>                       a line refused, or the queue full
 *   L <count>                      output lost because the host was not reading
 *
 * PLAY (play.h, docs/control-path.md): with a good table in flash the board drives the motors
 * from the levers by itself, from power-on, host or no host. Every frame is still reported as
 * an R line. Its F5 frames share bus A with the host's, one frame in flight at a time; a bench
 * run that wants the motors to itself sends 'P 0' first.
 *
 * Runs as the application under the USB loader. It feeds the loader's watchdog from the main
 * loop, host or no host: this board has to run with the Pi absent.
 */
#include <string.h>
#include "ch32v30x.h"
#include "link.h"
#include "play.h"
#if REV == 1
#include "ch32v30x_usbfs_device.h"
#include "UART.h"
#endif

#define VERSION 1

static uint8_t out_buf[8192];       /* us -> host */
static volatile uint16_t out_head, out_tail;
static uint32_t out_lost;
#if REV == 1
static uint8_t out_zlp;
#endif

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

#if REV != 1
static void out_pump(void)
{   /* whole lines only, so a frame lost on the way loses lines and never splices two */
    static uint8_t pkt[FRAME_MAX];
    if (link_tx_busy() || out_tail == out_head) return;
    uint16_t n = 0, whole = 0, at = out_tail;
    __disable_irq();
    while (n < sizeof pkt && at != out_head) {
        pkt[n++] = out_buf[at];
        at = (uint16_t)((at + 1) % sizeof out_buf);
        if (pkt[n - 1] == '\n') whole = n;
    }
    out_tail = (uint16_t)((out_tail + whole) % sizeof out_buf);
    __enable_irq();
    if (whole) link_send(pkt, whole);
}
#else
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
#endif

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
static volatile uint8_t  play_flying;       /* ...one of play's, on bus A */
static play_t play;

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
        play_frame_t pf = { m.IDE == CAN_Id_Extended ? m.ExtId : m.StdId, m.IDE == CAN_Id_Extended,
                            (uint8_t)(m.DLC > 8 ? 8 : m.DLC), {0} };
        memcpy(pf.d, m.Data, pf.len);
        play_rx(&play, (uint8_t)bus, &pf, (uint32_t)t);
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
        if (bus == 0 && play_flying) play_flying = 0;
        else if (flying[bus]) { say_ev('D', flying_seq[bus], bus, t, ok); flying[bus] = 0; }
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
    if (j->bus == 0 && play_flying) return -1;
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
        if (flying[j->bus] || (j->bus == 0 && play_flying) || now_us() < j->t) return;
        if (can_send(j) < 0) return;
        q_tail = (q_tail + 1) % NQ;
    }
}

static const char *r_num(const char *s, uint64_t *v, int base);

/* ---- play: the levers drive the motors -------------------------------------------------- */
static play_table_t stage;                  /* a table on its way in from the host */
static play_frame_t play_out;
static uint8_t play_have;

static void play_run(void)
{
    if (!play_have) {
        __disable_irq();                    /* play_rx runs in the receive interrupts */
        play_have = (uint8_t)play_poll(&play, (uint32_t)now_us(), &play_out);
        __enable_irq();
    }
    if (!play_have || flying[0] || play_flying) return;
    CanTxMsg m = {0};
    m.StdId = play_out.id; m.IDE = CAN_Id_Standard; m.RTR = CAN_RTR_Data; m.DLC = play_out.len;
    memcpy(m.Data, play_out.d, play_out.len);
    __disable_irq();
    play_flying = 1;
    if (CAN_Transmit(CAN1, &m) == CAN_TxStatus_NoMailBox) play_flying = 0;
    else play_have = 0;
    __enable_irq();
}

static int table_save(void)
{   /* the staged table into its sector, then play from what landed there */
    static uint32_t page[PAGE / 4];
    const uint8_t *src = (const uint8_t *)&stage;
    if (!play_table_ok(&stage)) return 0;
    if (FLASH_ROM_ERASE(FLASH_BASE_ADDR + TABLE_ORG, SECTOR) != FLASH_COMPLETE) return 0;
    for (uint32_t at = 0; at < sizeof stage; at += PAGE) {
        uint8_t *d = (uint8_t *)page;
        for (uint32_t i = 0; i < PAGE; i++) d[i] = at + i < sizeof stage ? src[at + i] : 0xFF;
        if (FLASH_ROM_WRITE(FLASH_BASE_ADDR + TABLE_ORG + at, page, PAGE) != FLASH_COMPLETE) return 0;
    }
    __disable_irq();
    int ok = play_load(&play, (const play_table_t *)(FLASH_BASE_ADDR + TABLE_ORG));
    __enable_irq();
    return ok;
}

static void play_line(const char *s)
{
    char l[64], *p = l;
    uint64_t v;
    while (*s == ' ') s++;
    if (!*s) {
        *p++ = 'P'; *p++ = ' '; *p++ = (char)('0' + play.ok); *p++ = ' '; *p++ = (char)('0' + play.on);
        *p++ = ' '; p = w_dec(p, play.moves); *p++ = ' ';
        for (int i = 0; i < PLAY_STRINGS; i++) *p++ = (char)('0' + play.state[i]);
        *p++ = ' '; p = w_hex(p, play.ok ? play.t.crc : 0, 8); *p++ = '\n';
        out_put(l, (uint16_t)(p - l));
        return;
    }
    if ((*s == '0' || *s == '1') && !s[1]) { play.on = (uint8_t)(*s - '0'); say("OK P\n"); return; }
    if (*s == 'Z' && !s[1]) {
        __disable_irq(); play_rebase(&play); __enable_irq();
        say("OK P\n"); return;
    }
    if (*s == 'S' && !s[1]) { say(table_save() ? "OK P S\n" : "E table\n"); return; }
    if (*s == 'W' && (s = r_num(s + 1, &v, 10))) {
        uint8_t *d = (uint8_t *)&stage;
        while (*s == ' ') s++;
        for (; s[0] && s[1]; s += 2, v++) {
            uint64_t b; char two[3] = { s[0], s[1], 0 };
            if (v >= sizeof stage || !r_num(two, &b, 16)) { say("E line\n"); return; }
            d[v] = (uint8_t)b;
        }
        if (!*s) { say("OK P\n"); return; }
    }
    say("E line\n");
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
        say("I public-steel-guitar-motor-bench "); p = w_dec(l, VERSION); *p++ = ' '; p = w_dec(p, now_us());
        *p++ = '\n'; out_put(l, (uint16_t)(p - l)); return;
    case 'T':
        p = l; *p++ = 'T'; *p++ = ' '; p = w_dec(p, now_us()); *p++ = '\n';
        out_put(l, (uint16_t)(p - l)); return;
    case 'V': {
        uint64_t bus;
        RCC_ClocksTypeDef ck;
        if (!r_num(s + 1, &bus, 10) || bus > 1) break;
        RCC_GetClocksFreq(&ck);
        p = l;
        *p++ = 'V'; *p++ = ' '; p = w_hex(p, BUS[bus]->ERRSR, 8); *p++ = ' ';
        p = w_hex(p, BUS[bus]->TSTATR, 8); *p++ = ' '; p = w_dec(p, ck.PCLK1_Frequency); *p++ = '\n';
        out_put(l, (uint16_t)(p - l));
        return;
    }
    case 'C':
        q_tail = q_head; say("OK C\n"); return;
#if REV != 1
    case 'F':
        p = l; *p++ = 'F'; *p++ = ' '; p = w_dec(p, link_bad()); *p++ = '\n';
        out_put(l, (uint16_t)(p - l)); return;
#endif
    case 'B': {
        uint64_t bus;
        if (!s[1]) { reset_to(GO_LOADER); }
        if ((s = r_num(s + 1, &bus, 10)) && bus <= 1 && r_num(s, &v, 10)
                && can_rate((int)bus, (uint32_t)v) == 0) { say("OK B\n"); return; }
        break; }
    case 'P':
        play_line(s + 1); return;
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
#if REV != 1
    static uint8_t pkt[LINK_PACKET];
    int got = link_take(pkt);
    if (got >= 0) n = 0;            /* a line never spans frames: the host sends whole ones */
#else
    uint8_t pkt[DEF_USBD_FS_PACK_SIZE];
    int got = link_take(pkt);
#endif
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
    play_init(&play, (const play_table_t *)(FLASH_BASE_ADDR + TABLE_ORG));
    link_init();
    can_setup();
    uint32_t lost_said = 0;
    while (1) {
        IWDG_ReloadCounter();           /* boot.c started it */
        q_run();
        play_run();
        in_pump();
        q_run();
        play_run();
        if (out_lost != lost_said && out_head == out_tail) {
            char l[24], *p = l; lost_said = out_lost;
            *p++ = 'L'; *p++ = ' '; p = w_dec(p, lost_said); *p++ = '\n';
            out_put(l, (uint16_t)(p - l));
        }
        out_pump();
    }
}
