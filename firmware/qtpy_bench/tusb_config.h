/* TinyUSB: one full-speed serial port on the CH32V203's USBD (TinyUSB's "FSDEV", root port 0). */
#ifndef TUSB_CONFIG_H_
#define TUSB_CONFIG_H_

#define CFG_TUSB_MCU              OPT_MCU_CH32V20X
#define CFG_TUD_WCH_USBIP_FSDEV   1
#define CFG_TUSB_OS               OPT_OS_NONE
#define CFG_TUSB_DEBUG            0
#define BOARD_TUD_RHPORT          0
#define CFG_TUD_ENABLED           1
#define CFG_TUD_MAX_SPEED         OPT_MODE_FULL_SPEED
#define CFG_TUSB_MEM_SECTION
#define CFG_TUSB_MEM_ALIGN        __attribute__((aligned(4)))
#define CFG_TUD_ENDPOINT0_SIZE    64

#define CFG_TUD_CDC               1
#define CFG_TUD_MSC               0
#define CFG_TUD_HID               0
#define CFG_TUD_MIDI              0
#define CFG_TUD_VENDOR            0
#define CFG_TUD_CDC_RX_BUFSIZE    256
#define CFG_TUD_CDC_TX_BUFSIZE    256
#define CFG_TUD_CDC_EP_BUFSIZE    64

#endif
