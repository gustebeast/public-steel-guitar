# motor_ctrl firmware, built on the Pi with the distribution's RISC-V GCC against WCH's own
# library. WCH's files are NOT in this repository: point WCH at a checkout of
# https://github.com/openwch/ch32v307 (the bench Pi has one at ~/src/ch32v307).
#
#   make              build/boot.bin and build/main.bin
#   make boot         write the loader with wlink through the WCH-LinkE. Once, or to recover
#   make usb          write the application over USB, through the loader
#   make isp          write the loader with wchisp through WCH's ROM loader on J4 (BOOT0 high
#                     at power-up): the way back with no probe
#
# REV=1 (the default) is the board in hand: the MCU's own USB on J4. REV=2 is the board with U7, a
# CH340C on USART1: every line goes in a checked frame (frame.h, link_uart.c), `make REV=2 usb`
# writes through the same loader over that, and `make REV=2 isp` needs no hand on the board -- the
# host sets BOOT0 and pulses reset through U7's DTR# / RTS# (bench/publicbench/motorflash.py).
REV   ?= 1
WCH   ?= $(HOME)/src/ch32v307
EXAM  := $(WCH)/EVT/EXAM
CDC   := $(EXAM)/USB/USBFS/DEVICE/SimulateCDC/User
CROSS ?= riscv64-unknown-elf-
# REV=1 builds where it always has; REV=2 beside it, so a switch never links the other one's objects
B     := build$(if $(filter-out 1,$(REV)),/r$(REV))

VSRC := $(EXAM)/SRC/Core/core_riscv.c \
        $(wildcard $(EXAM)/SRC/Peripheral/src/*.c) \
        $(CDC)/system_ch32v30x.c
ifeq ($(REV),1)
VSRC += $(CDC)/USB_Device/ch32v30x_usbfs_device.c $(CDC)/USB_Device/usb_desc.c
LINK := $(B)/link.o
else
LINK := $(B)/link_uart.o $(B)/frame.o
endif
VOBJ := $(patsubst %.c,$(B)/v/%.o,$(notdir $(VSRC)))
COMMON := $(LINK) $(B)/startup.o $(VOBJ)

CFLAGS := -march=rv32imac_zicsr_zifencei -mabi=ilp32 -msmall-data-limit=8 -Os -g \
          -ffunction-sections -fdata-sections -fno-common -Wall \
          --specs=picolibc.specs -DCH32V30x_D8C -DUSB_VID=0xCAFE -DUSB_PID=0x4008 -DREV=$(REV) \
          -I. -I$(EXAM)/SRC/Core -I$(EXAM)/SRC/Peripheral/inc -I$(EXAM)/SRC/Debug \
          -I$(CDC) -I$(CDC)/USB_Device -I$(CDC)/UART
LDFLAGS := -nostartfiles -Wl,--gc-sections

all: $(B)/boot.bin $(B)/main.bin

vpath %.c . $(sort $(dir $(VSRC)))

$(B)/v/%.c: %.c | $(B)/v
	sed -e 's/interrupt("WCH-Interrupt-fast")/interrupt/' -e 's/DEF_USB_VID/USB_VID/g' -e 's/DEF_USB_PID/USB_PID/g' $< > $@

# copied in, so that its #include "link.h" finds this board's and not the one beside it
$(B)/v/boot.c: ../output_panel/boot.c | $(B)/v
	cp $< $@

$(B)/boot.o: $(B)/v/boot.c link.h frame.h
	$(CROSS)gcc $(CFLAGS) -c $< -o $@

$(B)/v/%.o: $(B)/v/%.c
	$(CROSS)gcc $(CFLAGS) -w -c $< -o $@

$(B)/%.o: %.c link.h frame.h | $(B)/v
	$(CROSS)gcc $(CFLAGS) -c $< -o $@

# WCH's startup drops to user mode for main. The loader must stay in machine mode, because the
# application's startup, which it jumps to, writes machine CSRs.
$(B)/v/startup.S: $(EXAM)/SRC/Startup/startup_ch32v30x_D8C.S | $(B)/v
	sed 's/li t0, 0x6088/li t0, 0x7888/' $< > $@
	grep -q 'li t0, 0x7888' $@

$(B)/startup.o: $(B)/v/startup.S
	$(CROSS)gcc $(CFLAGS) -c $< -o $@

# as this chip's option bytes have it (wlink: 288 K): 288 K flash, 32 K RAM, less the 16 bytes
# at its top that carry BOOT_WORDS over a reset
$(B)/boot.ld: $(EXAM)/SRC/Ld/Link.ld | $(B)/v
	sed -e 's/FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 288K/FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 28K/' \
	    -e 's/RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 32K/RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 32752/' $< > $@
$(B)/main.ld: $(EXAM)/SRC/Ld/Link.ld | $(B)/v
	sed -e 's/FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 288K/FLASH (rx) : ORIGIN = 0x00008000, LENGTH = 256K/' \
	    -e 's/RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 32K/RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 32752/' $< > $@

$(B)/%.elf: $(B)/%.o $(COMMON) $(B)/%.ld
	$(CROSS)gcc $(CFLAGS) $< $(COMMON) -T$(B)/$*.ld $(LDFLAGS) -Wl,-Map,$(B)/$*.map -o $@
	$(CROSS)size $@

$(B)/%.bin: $(B)/%.elf
	$(CROSS)objcopy -O binary $< $@

$(B)/v:
	mkdir -p $@

boot: $(B)/boot.bin
	wlink flash --address 0x08000000 $<

BENCH := PYTHONPATH=$(CURDIR)/../../bench python3 -m publicbench.motorflash
ifeq ($(REV),1)
usb: $(B)/main.bin
	python3 ../output_panel/usbflash.py --ids cafe:4008 $<

# the .bin, never the .elf: wchisp sizes its erase from the file
isp: $(B)/boot.bin
	wchisp flash $<
else
usb: $(B)/main.bin
	$(BENCH) $<

isp: $(B)/boot.bin
	$(BENCH) --rom $<
endif

clean:
	rm -rf $(B)

.PHONY: all boot usb isp clean
.SECONDARY:
