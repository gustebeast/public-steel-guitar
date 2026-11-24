# QT Py CH32V203 open-loop bench firmware (README.md), built on the Pi with the distribution's
# RISC-V GCC against WCH's library and TinyUSB. Neither is in this repository: point WCH at a
# checkout of https://github.com/openwch/ch32v20x and TUSB at https://github.com/hathach/tinyusb
# (the bench Pi has both, at ~/src/ch32v20x and ~/src/tinyusb).
#
#   make        build/bench.bin
#   make isp    write it through the chip's ROM loader with wchisp, over the QT Py's own USB:
#               unplug the QT Py, hold BOOT, plug it back in, release, then `make isp`
#
# axis.c, tmc.c and bench.c have no hardware in them; bench/tests/test_qtpy_bench.py compiles
# them natively.
WCH   ?= $(HOME)/src/ch32v20x
TUSB  ?= $(HOME)/src/tinyusb
EXAM  := $(WCH)/EVT/EXAM
CROSS ?= riscv64-unknown-elf-
B     := build

VSRC := $(EXAM)/SRC/Core/core_riscv.c \
        $(patsubst %,$(EXAM)/SRC/Peripheral/src/ch32v20x_%.c,gpio rcc tim usart misc)
TSRC := $(TUSB)/src/tusb.c $(TUSB)/src/common/tusb_fifo.c $(TUSB)/src/device/usbd.c \
        $(TUSB)/src/class/cdc/cdc_device.c \
        $(TUSB)/src/portable/st/stm32_fsdev/dcd_stm32_fsdev.c \
        $(TUSB)/src/portable/st/stm32_fsdev/fsdev_common.c
VOBJ := $(patsubst %.c,$(B)/v/%.o,$(notdir $(VSRC))) $(B)/v/system_ch32v20x.o
TOBJ := $(patsubst %.c,$(B)/t/%.o,$(notdir $(TSRC)))
OBJ  := $(B)/main.o $(B)/bench.o $(B)/axis.o $(B)/tmc.o $(B)/usb_descriptors.o $(B)/startup.o \
        $(VOBJ) $(TOBJ)

CFLAGS := -march=rv32imac_zicsr_zifencei -mabi=ilp32 -msmall-data-limit=8 -Os -g \
          -ffunction-sections -fdata-sections -fno-common -Wall -Wextra \
          --specs=picolibc.specs -DCH32V20x_D6 \
          -I. -I$(EXAM)/SRC/Core -I$(EXAM)/SRC/Peripheral/inc -I$(EXAM)/SRC/Debug -I$(B)/v -I$(TUSB)/src
LDFLAGS := -nostartfiles -Wl,--gc-sections

all: $(B)/bench.bin

vpath %.c . $(sort $(dir $(VSRC) $(TSRC)))

$(B)/v/%.c: %.c | $(B)/v
	sed -e 's/interrupt("WCH-Interrupt-fast")/interrupt/' $< > $@

# WCH's system file, from the GPIO example, at 96 MHz off the internal oscillator: the QT Py has
# no crystal. 96 MHz gives the USB its 48 MHz at PLL / 2. Checked, so a changed upstream file
# stops the build.
$(B)/v/system_ch32v20x.c: $(EXAM)/GPIO/GPIO_Toggle/User/system_ch32v20x.c | $(B)/v
	sed -e 's|^#define SYSCLK_FREQ_96MHz_HSE|//#define SYSCLK_FREQ_96MHz_HSE|' \
	    -e 's|^//#define SYSCLK_FREQ_96MHz_HSI|#define SYSCLK_FREQ_96MHz_HSI|' $< > $@
	grep -q '^#define SYSCLK_FREQ_96MHz_HSI' $@
	test $$(grep -c '^#define SYSCLK_FREQ' $@) = 1
# ...with the two headers ch32v20x.h pulls in from an example's User folder
USER := $(EXAM)/GPIO/GPIO_Toggle/User
HDRS := $(B)/v/system_ch32v20x.h $(B)/v/ch32v20x_conf.h $(B)/v/ch32v20x_it.h
$(B)/v/%.h: $(USER)/%.h | $(B)/v
	cp $< $@

# WCH's code against picolibc: their files use size_t with no <stddef.h>
$(B)/v/%.o: $(B)/v/%.c $(HDRS)
	$(CROSS)gcc $(CFLAGS) -include stddef.h -w -c $< -o $@

$(B)/t/%.o: %.c tusb_config.h $(HDRS) | $(B)/t
	$(CROSS)gcc $(CFLAGS) -w -c $< -o $@

$(B)/%.o: %.c axis.h tmc.h bench.h tusb_config.h $(HDRS) | $(B)/v
	$(CROSS)gcc $(CFLAGS) -c $< -o $@

$(B)/startup.o: $(EXAM)/SRC/Startup/startup_ch32v20x_D6.S | $(B)/v
	$(CROSS)gcc $(CFLAGS) -c $< -o $@

# CH32V203G6: 32 K flash, 10 K RAM. WCH's file is written for the 64 K parts.
$(B)/bench.ld: $(EXAM)/SRC/Ld/Link.ld | $(B)/v
	sed -e 's/FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 64K/FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 32K/' \
	    -e 's/RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 20K/RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 10K/' $< > $@
	grep -q 'LENGTH = 32K' $@ && grep -q 'LENGTH = 10K' $@

$(B)/bench.elf: $(OBJ) $(B)/bench.ld
	$(CROSS)gcc $(CFLAGS) $(OBJ) -T$(B)/bench.ld $(LDFLAGS) -Wl,-Map,$(B)/bench.map -o $@
	$(CROSS)size $@

$(B)/%.bin: $(B)/%.elf
	$(CROSS)objcopy -O binary $< $@

$(B)/v $(B)/t:
	mkdir -p $@

# the .bin, never the .elf: wchisp sizes its erase from the file
isp: $(B)/bench.bin
	wchisp flash $<

clean:
	rm -rf $(B)

.PHONY: all isp clean
.SECONDARY:
