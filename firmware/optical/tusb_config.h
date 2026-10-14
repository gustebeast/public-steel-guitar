/* TinyUSB: a high-speed device on the OTG_HS core (root hub port 1) with two serial ports,
   the first for commands and the second for samples. */
#ifndef TUSB_CONFIG_H_
#define TUSB_CONFIG_H_

#define CFG_TUSB_MCU              OPT_MCU_STM32H7
#define CFG_TUSB_OS               OPT_OS_NONE
#define CFG_TUSB_DEBUG            0
#define BOARD_TUD_RHPORT          1
#define BOARD_TUD_MAX_SPEED       OPT_MODE_HIGH_SPEED
#define CFG_TUD_ENABLED           1
#define CFG_TUD_MAX_SPEED         BOARD_TUD_MAX_SPEED
#define CFG_TUSB_MEM_SECTION
#define CFG_TUSB_MEM_ALIGN        __attribute__((aligned(4)))
#define CFG_TUD_ENDPOINT0_SIZE    64

#define CFG_TUD_CDC               2
#define CFG_TUD_MSC               0
#define CFG_TUD_HID               0
#define CFG_TUD_MIDI              0
#define CFG_TUD_VENDOR            0
#define CFG_TUD_CDC_NOTIFY        1
#define CFG_TUD_CDC_RX_BUFSIZE    512
/* a block of all five converters is 38416 bytes and goes in whole or not at all */
#define CFG_TUD_CDC_TX_BUFSIZE    49152
#define CFG_TUD_CDC_RX_EPSIZE     512
#define CFG_TUD_CDC_TX_EPSIZE     512

#endif
