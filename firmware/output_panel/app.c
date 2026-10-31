/* output_panel's first application: proves the loader by being replaceable. Answers ? with
 * its name and version, and B by going back to the loader. Real firmware keeps the B. */
#include <string.h>
#include "UART.h"
#include "ch32v30x_usbhs_device.h"
#include "link.h"

void Delay_Ms(uint32_t n);
void NMI_Handler(void) __attribute__((interrupt));
void HardFault_Handler(void) __attribute__((interrupt));
void NMI_Handler(void) { }
void HardFault_Handler(void) { NVIC_SystemReset(); while (1) { } }

int main(void)
{
    link_init();
    static uint8_t pkt[DEF_USB_HS_PACK_LEN];
    while (1) {
        int got = link_take(pkt);
        for (int i = 0; i < got; i++) {
            if (pkt[i] == '?') link_say("APP output_panel " VERSION "\n");
            if (pkt[i] == 'B') { link_say("OK\n"); Delay_Ms(20); reset_to(GO_LOADER); }
        }
    }
}
