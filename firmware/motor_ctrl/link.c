/* USB serial for motor_ctrl's two images, on WCH's USBFS CDC device (PA11/PA12, J4). Their
 * UART bridge's variables, with no UART behind them. */
#include <string.h>
#include "UART.h"
#include "ch32v30x_usbfs_device.h"
#include "link.h"

volatile UART_CTL Uart;
volatile uint32_t UARTx_Rx_DMACurCount, UARTx_Rx_DMALastCount;
__attribute__((aligned(4))) uint8_t UART2_Tx_Buf[DEF_UARTx_TX_BUF_LEN];   /* host -> us */

static uint32_t ticks_per_us;

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

void UART2_USB_Init(void) { }

void UART2_ParaInit(uint8_t mode)
{
    memset((void *)&Uart, 0, sizeof Uart);
    if (mode) {
        Uart.Com_Cfg[0] = (uint8_t)115200; Uart.Com_Cfg[1] = (uint8_t)(115200 >> 8);
        Uart.Com_Cfg[2] = (uint8_t)(115200 >> 16); Uart.Com_Cfg[6] = 8;
    }
}

void link_init(void)
{
    SystemCoreClockUpdate();
    ticks_per_us = SystemCoreClock / 1000000;
    SysTick->CTLR = 0; SysTick->CNT = 0; SysTick->CMP = ~0ULL;
    SysTick->CTLR = 0x5;            /* count HCLK, upward, no reload */
    UART2_ParaInit(1);
    USBFS_RCC_Init();
    USBFS_Device_Init(ENABLE);
}

int link_up(void) { return USBFS_DevEnumStatus != 0; }

void link_send(const void *d, uint16_t n)
{
    const uint8_t *s = d;
    uint64_t give_up = now_us() + 200000;
    while (n) {
        uint16_t k = n > 64 ? 64 : n;
        while (USBFS_Endp_Busy[DEF_UEP3])
            if (now_us() > give_up) return;     /* nobody is reading */
        NVIC_DisableIRQ(USBFS_IRQn);
        USBFS_Endp_DataUp(DEF_UEP3, (uint8_t *)s, k, DEF_UEP_CPY_LOAD);
        NVIC_EnableIRQ(USBFS_IRQn);
        s += k; n -= k;
    }
}

void link_say(const char *s) { link_send(s, (uint16_t)strlen(s)); }

int link_take(uint8_t *dst)
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

void reset_to(uint32_t what)
{
    BOOT_WORDS[0] = what; BOOT_WORDS[1] = ~what;
    NVIC_SystemReset();
    while (1) { }
}
