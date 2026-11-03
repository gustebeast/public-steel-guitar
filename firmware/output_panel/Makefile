# output_panel firmware, built on the Pi with the distribution's RISC-V GCC against WCH's own
# library. WCH's files are NOT in this repository: point WCH at a checkout of
# https://github.com/openwch/ch32v307 (the bench Pi has one at ~/src/ch32v307).
#
#   make              build/boot.bin and build/app.bin
#   make boot         write the loader with wlink through the WCH-LinkE. Once, or to recover
#   make usb          write the application over USB, through the loader
WCH   ?= $(HOME)/src/ch32v307
EXAM  := $(WCH)/EVT/EXAM
CDC   := $(EXAM)/USB/USBHS/DEVICE/SimulateCDC/User
CROSS ?= riscv64-unknown-elf-
VERSION ?= 1
# the board: 1 as in hand, 2 adds J1's port and the inlet meter (make REV=2)
REV   ?= 1
B     := build

VSRC := $(EXAM)/SRC/Core/core_riscv.c \
        $(wildcard $(EXAM)/SRC/Peripheral/src/*.c) \
        $(CDC)/system_ch32v30x.c $(CDC)/USB_Device/ch32v30x_usbhs_device.c $(CDC)/USB_Device/usb_desc.c
VOBJ := $(patsubst %.c,$(B)/v/%.o,$(notdir $(VSRC)))
COMMON := $(B)/link.o $(B)/startup.o $(VOBJ)

CFLAGS := -march=rv32imac_zicsr_zifencei -mabi=ilp32 -msmall-data-limit=8 -Os -g \
          -ffunction-sections -fdata-sections -fno-common -Wall \
          --specs=picolibc.specs -DCH32V30x_D8C -DVERSION='"$(VERSION)"' -DREV=$(REV) \
          -I. -I$(EXAM)/SRC/Core -I$(EXAM)/SRC/Peripheral/inc -I$(EXAM)/SRC/Debug \
          -I$(CDC) -I$(CDC)/USB_Device -I$(CDC)/UART
LDFLAGS := -nostartfiles -Wl,--gc-sections

all: $(B)/boot.bin $(B)/app.bin

vpath %.c $(sort $(dir $(VSRC)))

$(B)/v/%.c: %.c | $(B)/v
	sed 's/interrupt("WCH-Interrupt-fast")/interrupt/' $< > $@

$(B)/v/%.o: $(B)/v/%.c
	$(CROSS)gcc $(CFLAGS) -w -c $< -o $@

$(B)/%.o: %.c link.h | $(B)/v
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
$(B)/app.ld: $(EXAM)/SRC/Ld/Link.ld | $(B)/v
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

usb: $(B)/app.bin
	python3 usbflash.py $<

clean:
	rm -rf $(B)

.PHONY: all boot usb clean
.SECONDARY:
