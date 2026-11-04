# lever_sensor firmware, built on the Pi with the distribution's RISC-V GCC against WCH's own
# library. WCH's files are NOT in this repository: point WCH at a checkout of
# https://github.com/openwch/ch32v20x (the bench Pi has one at ~/src/ch32v20x).
#
#   make              build/lever.bin
#   make swd          write it with wlink through the WCH-LinkE (the pogo jig, src/lever_jig.py)
#
# lever.c is the logic and has no hardware in it; bench/tests/test_levers.py compiles it natively.
WCH   ?= $(HOME)/src/ch32v20x
EXAM  := $(WCH)/EVT/EXAM
CROSS ?= riscv64-unknown-elf-
B     := build

VSRC := $(EXAM)/SRC/Core/core_riscv.c \
        $(wildcard $(EXAM)/SRC/Peripheral/src/*.c)
VOBJ := $(patsubst %.c,$(B)/v/%.o,$(notdir $(VSRC))) $(B)/v/system_ch32v20x.o
OBJ  := $(B)/main.o $(B)/lever.o $(B)/ma730.o $(B)/startup.o $(VOBJ)

CFLAGS := -march=rv32imac_zicsr_zifencei -mabi=ilp32 -msmall-data-limit=8 -Os -g \
          -ffunction-sections -fdata-sections -fno-common -Wall -Wextra \
          --specs=picolibc.specs -DCH32V20x_D6 \
          -I. -I$(EXAM)/SRC/Core -I$(EXAM)/SRC/Peripheral/inc -I$(EXAM)/SRC/Debug -I$(B)/v
LDFLAGS := -nostartfiles -Wl,--gc-sections

all: $(B)/lever.bin

vpath %.c . $(sort $(dir $(VSRC)))

$(B)/v/%.c: %.c | $(B)/v
	sed -e 's/interrupt("WCH-Interrupt-fast")/interrupt/' $< > $@

# WCH's system file, from the GPIO example, at 48 MHz off the crystal: the MA730's SPI divider and
# the CAN timing are both worked from it. Checked, so a changed upstream file stops the build.
$(B)/v/system_ch32v20x.c: $(EXAM)/GPIO/GPIO_Toggle/User/system_ch32v20x.c | $(B)/v
	sed -e 's|^#define SYSCLK_FREQ_96MHz_HSE|//#define SYSCLK_FREQ_96MHz_HSE|' \
	    -e 's|^//#define SYSCLK_FREQ_48MHz_HSE|#define SYSCLK_FREQ_48MHz_HSE|' $< > $@
	grep -q '^#define SYSCLK_FREQ_48MHz_HSE' $@
	test $$(grep -c '^#define SYSCLK_FREQ' $@) = 1
# ...with the two headers ch32v20x.h pulls in from an example's User folder
USER := $(EXAM)/GPIO/GPIO_Toggle/User
HDRS := $(B)/v/system_ch32v20x.h $(B)/v/ch32v20x_conf.h $(B)/v/ch32v20x_it.h
$(B)/v/%.h: $(USER)/%.h | $(B)/v
	cp $< $@

# WCH's code against picolibc: debug.c (not built here) and others use ptrdiff_t / size_t with
# no <stddef.h>; glibc's headers happened to bring it in, picolibc's do not. Their files only.
$(B)/v/%.o: $(B)/v/%.c $(HDRS)
	$(CROSS)gcc $(CFLAGS) -include stddef.h -w -c $< -o $@

$(B)/%.o: %.c lever.h ma730.h $(HDRS) | $(B)/v
	$(CROSS)gcc $(CFLAGS) -c $< -o $@

$(B)/startup.o: $(EXAM)/SRC/Startup/startup_ch32v20x_D6.S | $(B)/v
	$(CROSS)gcc $(CFLAGS) -c $< -o $@

# CH32V203G6: 32 K flash, 10 K RAM. The flash stops short of the last 256-byte page, which holds
# the calibration (main.c CFG_AT). WCH's file is written for the 64 K parts.
$(B)/lever.ld: $(EXAM)/SRC/Ld/Link.ld | $(B)/v
	sed -e 's/FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 64K/FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 32512/' \
	    -e 's/RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 20K/RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 10K/' $< > $@
	grep -q 'LENGTH = 32512' $@ && grep -q 'LENGTH = 10K' $@

$(B)/lever.elf: $(OBJ) $(B)/lever.ld
	$(CROSS)gcc $(CFLAGS) $(OBJ) -T$(B)/lever.ld $(LDFLAGS) -Wl,-Map,$(B)/lever.map -o $@
	$(CROSS)size $@

$(B)/%.bin: $(B)/%.elf
	$(CROSS)objcopy -O binary $< $@

$(B)/v:
	mkdir -p $@

swd: $(B)/lever.bin
	wlink flash --address 0x08000000 $<

clean:
	rm -rf $(B)

.PHONY: all swd clean
.SECONDARY:
