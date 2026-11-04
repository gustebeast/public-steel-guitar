/* R2's link (make REV=2): J4 is U7, a CH340C, on USART1 (PA9 TX, PA10 RX) at LINK_BAUD, in
 * frames (frame.h). The same calls as link.c's USB CDC, so boot.c and main.c sit on either.
 *
 * RX: DMA1 channel 5, circular, into a ring the main loop drains: no interrupt, and nothing is
 * lost while a frame is being acted on as long as the loop comes round within the ring's time
 * (1024 bytes, 5 ms at 2 Mbaud; the host waits for each reply in the loader, and the bench's
 * lines are short). A lap shows up as frames whose CRC fails: link_bad() counts them.
 * TX: DMA1 channel 4, one frame at a time from tx[].
 *
 * BOOT0 / NRST are U7's DTR# / RTS# through Q1 / Q2, and only act when the two DIFFER: the
 * host opening or closing the port (both together) does nothing here. */
#include <string.h>
#include "link.h"

#define RING 1024u

static uint32_t ticks_per_us;
static uint8_t ring[RING];
static uint32_t ring_rd;
static uint8_t tx[FRAME_WIRE];
static frame_rx_t rx;

uint64_t now_us(void)
{
    volatile uint32_t *p = (volatile uint32_t *)&SysTick->CNT;
    uint32_t hi, lo;
    do { hi = p[1]; lo = p[0]; } while (hi != p[1]);
    return (((uint64_t)hi << 32) | lo) / ticks_per_us;
}

void Delay_Us(uint32_t n)
{
    uint64_t end = now_us() + n;
    while (now_us() < end) { }
}

void Delay_Ms(uint32_t n) { Delay_Us(n * 1000); }

void link_init(void)
{
    SystemCoreClockUpdate();
    ticks_per_us = SystemCoreClock / 1000000;
    SysTick->CTLR = 0; SysTick->CNT = 0; SysTick->CMP = ~0ULL;
    SysTick->CTLR = 0x5;            /* count HCLK, upward, no reload */

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_USART1, ENABLE);
    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_DMA1, ENABLE);
    GPIO_InitTypeDef g = {0};
    g.GPIO_Speed = GPIO_Speed_50MHz;
    g.GPIO_Pin = GPIO_Pin_9; g.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_Init(GPIOA, &g);
    g.GPIO_Pin = GPIO_Pin_10; g.GPIO_Mode = GPIO_Mode_IPU;    /* idle high with no U7 */
    GPIO_Init(GPIOA, &g);

    USART_InitTypeDef u = {0};
    u.USART_BaudRate = LINK_BAUD;
    u.USART_WordLength = USART_WordLength_8b;
    u.USART_StopBits = USART_StopBits_1;
    u.USART_Parity = USART_Parity_No;
    u.USART_HardwareFlowControl = USART_HardwareFlowControl_None;
    u.USART_Mode = USART_Mode_Tx | USART_Mode_Rx;
    USART_Init(USART1, &u);

    DMA_InitTypeDef d = {0};
    d.DMA_PeripheralBaseAddr = (uint32_t)&USART1->DATAR;
    d.DMA_PeripheralInc = DMA_PeripheralInc_Disable;
    d.DMA_MemoryInc = DMA_MemoryInc_Enable;
    d.DMA_PeripheralDataSize = DMA_PeripheralDataSize_Byte;
    d.DMA_MemoryDataSize = DMA_MemoryDataSize_Byte;
    d.DMA_M2M = DMA_M2M_Disable;
    DMA_DeInit(DMA1_Channel5);                                  /* RX */
    d.DMA_MemoryBaseAddr = (uint32_t)ring;
    d.DMA_DIR = DMA_DIR_PeripheralSRC;
    d.DMA_BufferSize = RING;
    d.DMA_Mode = DMA_Mode_Circular;
    d.DMA_Priority = DMA_Priority_VeryHigh;
    DMA_Init(DMA1_Channel5, &d);
    DMA_DeInit(DMA1_Channel4);                                  /* TX */
    d.DMA_MemoryBaseAddr = (uint32_t)tx;
    d.DMA_DIR = DMA_DIR_PeripheralDST;
    d.DMA_BufferSize = 0;
    d.DMA_Mode = DMA_Mode_Normal;
    d.DMA_Priority = DMA_Priority_High;
    DMA_Init(DMA1_Channel4, &d);
    DMA_Cmd(DMA1_Channel5, ENABLE);
    USART_DMACmd(USART1, USART_DMAReq_Tx | USART_DMAReq_Rx, ENABLE);
    USART_Cmd(USART1, ENABLE);
}

int link_up(void) { return 1; }     /* a UART has no "enumerated": the host is there or not */

uint32_t link_bad(void) { return rx.bad; }

int link_tx_busy(void) { return DMA_GetCurrDataCounter(DMA1_Channel4) != 0; }

static void send_frame(const uint8_t *p, uint32_t n)
{
    uint64_t give_up = now_us() + 200000;
    while (link_tx_busy())
        if (now_us() > give_up) return;         /* a stuck UART: drop it, as USB's nobody-reading */
    uint32_t w = frame_encode(p, n, tx);
    DMA_Cmd(DMA1_Channel4, DISABLE);
    DMA_SetCurrDataCounter(DMA1_Channel4, (uint16_t)w);
    DMA_Cmd(DMA1_Channel4, ENABLE);
}

void link_send(const void *d, uint16_t n)
{   /* the callers' messages are lines, all far under FRAME_MAX: one frame each */
    const uint8_t *s = d;
    while (n) {
        uint16_t k = n > FRAME_MAX ? FRAME_MAX : n;
        send_frame(s, k);
        s += k; n -= k;
    }
}

void link_say(const char *s) { link_send(s, (uint16_t)strlen(s)); }

int link_take(uint8_t *dst)
{
    uint32_t wr = RING - DMA_GetCurrDataCounter(DMA1_Channel5);
    while (ring_rd != wr) {
        uint8_t c = ring[ring_rd];
        ring_rd = (ring_rd + 1) % RING;
        int got = frame_feed(&rx, c, dst);
        if (got >= 0) return got;
    }
    return -1;
}

void reset_to(uint32_t what)
{
    BOOT_WORDS[0] = what; BOOT_WORDS[1] = ~what;
    NVIC_SystemReset();
    while (1) { }
}
