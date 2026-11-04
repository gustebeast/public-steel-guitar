# lever_sensor firmware, built on the Pi with the distribution's RISC-V GCC against WCH's own
# library. WCH's files are NOT in this repository: point WCH at a checkout of
# https://github.com/openwch/ch32v20x (the bench Pi has one at ~/src/ch32v20x).
#
#   make              build/boot.bin (the CAN loader, 0x0000), build/lever.bin (the application,
#                     0x2800) and build/full.bin: both, with the loader's record of the application
#   make swd          write full.bin with wlink through the WCH-LinkE (the pogo jig, src/lever_jig.py):
#                     once per board, the first flash. Every later application goes over bus B:
#   make can SLOT=n   write lever.bin into lever n through its loader (bench/publicbench/leverflash.py)
#
# lever.c and ldr.c are the logic and have no hardware in them; bench/tests/test_levers.py compiles
# them natively. The flash map is in ldr.h.
WCH   ?= $(HOME)/src/ch32v20x
EXAM  := $(WCH)/EVT/EXAM
CROSS ?= riscv64-unknown-elf-
B     := build

VSRC := $(EXAM)/SRC/Core/core_riscv.c \
        $(wildcard $(EXAM)/SRC/Peripheral/src/*.c)
VOBJ := $(patsubst %.c,$(B)/v/%.o,$(notdir $(VSRC))) $(B)/v/system_ch32v20x.o
OBJ  := $(B)/main.o $(B)/hw.o $(B)/lever.o $(B)/ma730.o $(B)/startup.o $(VOBJ)
BOBJ := $(B)/boot.o $(B)/hw.o $(B)/lever.o $(B)/ldr.o $(B)/startup_m.o $(VOBJ)

CFLAGS := -march=rv32imac_zicsr_zifencei -mabi=ilp32 -msmall-data-limit=8 -Os -g \
          -ffunction-sections -fdata-sections -fno-common -Wall -Wextra \
          --specs=picolibc.specs -DCH32V20x_D6 \
          -I. -I$(EXAM)/SRC/Core -I$(EXAM)/SRC/Peripheral/inc -I$(EXAM)/SRC/Debug -I$(B)/v
LDFLAGS := -nostartfiles -Wl,--gc-sections

all: $(B)/full.bin

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

$(B)/%.o: %.c lever.h ldr.h hw.h ma730.h $(HDRS) | $(B)/v
	$(CROSS)gcc $(CFLAGS) -c $< -o $@

$(B)/startup.o: $(EXAM)/SRC/Startup/startup_ch32v20x_D6.S | $(B)/v
	$(CROSS)gcc $(CFLAGS) -c $< -o $@

# WCH's startup drops to user mode for main. The loader must stay in machine mode, because the
# application's startup, which it jumps to, writes machine CSRs (MPP = 3: 0x88 -> 0x1888)
$(B)/v/startup_m.S: $(EXAM)/SRC/Startup/startup_ch32v20x_D6.S | $(B)/v
	sed 's/li t0, 0x88\b/li t0, 0x1888/' $< > $@
	grep -q 'li t0, 0x1888' $@

$(B)/startup_m.o: $(B)/v/startup_m.S
	$(CROSS)gcc $(CFLAGS) -c $< -o $@

# CH32V203G6: 32 K flash, 10 K RAM (the C8T6 since 2026-11-03 has 64 K / 20 K; the map stays). The loader below APP_AT, the application from it to the
# loader's record page (ldr.h); both programs' RAM stops 16 short of the top, where BOOT_WORDS
# live through a reset. WCH's file is written for the 64 K parts.
RAM := -e 's/RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 20K/RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 10224/'
$(B)/boot.ld: $(EXAM)/SRC/Ld/Link.ld | $(B)/v
	sed -e 's/FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 64K/FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 0x2800/' $(RAM) $< > $@
	grep -q 'LENGTH = 0x2800' $@ && grep -q 'LENGTH = 10224' $@
$(B)/lever.ld: $(EXAM)/SRC/Ld/Link.ld | $(B)/v
	sed -e 's/FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 64K/FLASH (rx) : ORIGIN = 0x00002800, LENGTH = 0x5600/' $(RAM) $< > $@
	grep -q 'ORIGIN = 0x00002800, LENGTH = 0x5600' $@ && grep -q 'LENGTH = 10224' $@

$(B)/lever.elf: $(OBJ) $(B)/lever.ld
	$(CROSS)gcc $(CFLAGS) $(OBJ) -T$(B)/lever.ld $(LDFLAGS) -Wl,-Map,$(B)/lever.map -o $@
	$(CROSS)size $@

$(B)/boot.elf: $(BOBJ) $(B)/boot.ld
	$(CROSS)gcc $(CFLAGS) $(BOBJ) -T$(B)/boot.ld $(LDFLAGS) -Wl,-Map,$(B)/boot.map -o $@
	$(CROSS)size $@

# the SWD image: loader, application at APP_AT, and the record at REC_AT that lets the loader
# start it. It stops there: the config page (slot, calibration) above is not in the file.
$(B)/full.bin: $(B)/boot.bin $(B)/lever.bin image.py ldr.h
	python3 image.py $(B)/boot.bin $(B)/lever.bin $@

$(B)/%.bin: $(B)/%.elf
	$(CROSS)objcopy -O binary $< $@

$(B)/v:
	mkdir -p $@

swd: $(B)/full.bin
	wlink flash --address 0x08000000 $<

can: $(B)/lever.bin
	PYTHONPATH=$(CURDIR)/../../bench python3 -m publicbench.leverflash $(SLOT) $<

clean:
	rm -rf $(B)

.PHONY: all swd can clean
.SECONDARY:
