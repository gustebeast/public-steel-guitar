# motor_ctrl bench firmware, built with the distribution's RISC-V GCC against WCH's own
# library. WCH's files are NOT in this repository: point WCH at a checkout of
# https://github.com/openwch/ch32v307 (the bench Pi has one at ~/src/ch32v307).
#
#   make            build/motor_ctrl.bin
#   make flash      write it with wlink through the WCH-LinkE
#   make isp        write it with wchisp through WCH's ROM loader on J4 (BOOT0 high at power-up)
WCH   ?= $(HOME)/src/ch32v307
EXAM  := $(WCH)/EVT/EXAM
CDC   := $(EXAM)/USB/USBFS/DEVICE/SimulateCDC/User
CROSS ?= riscv64-unknown-elf-
B     := build

# Their sources are copied into build/ with two edits, because their compiler is a fork:
#   * interrupt("WCH-Interrupt-fast") is theirs alone -> the standard `interrupt`
#   * the chip's memory, which their linker script leaves at its smallest part
VSRC := $(EXAM)/SRC/Core/core_riscv.c \
        $(wildcard $(EXAM)/SRC/Peripheral/src/*.c) \
        $(CDC)/system_ch32v30x.c $(CDC)/USB_Device/ch32v30x_usbfs_device.c $(CDC)/USB_Device/usb_desc.c
VOBJ := $(patsubst %.c,$(B)/v/%.o,$(notdir $(VSRC)))
OBJ  := $(B)/main.o $(B)/startup.o $(VOBJ)

CFLAGS := -march=rv32imac_zicsr_zifencei -mabi=ilp32 -msmall-data-limit=8 -Os -g \
          -ffunction-sections -fdata-sections -fno-common -Wall \
          --specs=picolibc.specs -DCH32V30x_D8C \
          -I$(EXAM)/SRC/Core -I$(EXAM)/SRC/Peripheral/inc -I$(EXAM)/SRC/Debug \
          -I$(CDC) -I$(CDC)/USB_Device -I$(CDC)/UART
LDFLAGS := -T$(B)/link.ld -nostartfiles -Wl,--gc-sections -Wl,-Map,$(B)/motor_ctrl.map

all: $(B)/motor_ctrl.bin
	$(CROSS)size $(B)/motor_ctrl.elf

vpath %.c $(sort $(dir $(VSRC)))

$(B)/v/%.c: %.c | $(B)/v
	sed 's/interrupt("WCH-Interrupt-fast")/interrupt/' $< > $@

$(B)/v/%.o: $(B)/v/%.c
	$(CROSS)gcc $(CFLAGS) -w -c $< -o $@

$(B)/main.o: main.c | $(B)/v
	$(CROSS)gcc $(CFLAGS) -c $< -o $@

$(B)/startup.o: $(EXAM)/SRC/Startup/startup_ch32v30x_D8C.S | $(B)/v
	$(CROSS)gcc $(CFLAGS) -c $< -o $@

# CH32V307WCU6 as shipped: 256 K flash, 64 K RAM
$(B)/link.ld: $(EXAM)/SRC/Ld/Link.ld | $(B)/v
	sed -e 's/LENGTH = 288K/LENGTH = 256K/' -e 's/RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 32K/RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 64K/' $< > $@

$(B)/motor_ctrl.elf: $(OBJ) $(B)/link.ld
	$(CROSS)gcc $(CFLAGS) $(OBJ) $(LDFLAGS) -o $@

$(B)/motor_ctrl.bin: $(B)/motor_ctrl.elf
	$(CROSS)objcopy -O binary $< $@

$(B)/v:
	mkdir -p $@

flash: $(B)/motor_ctrl.bin
	wlink flash --address 0x08000000 $<

# the .bin, never the .elf: wchisp sizes its erase from the file
isp: $(B)/motor_ctrl.bin
	wchisp flash $<

clean:
	rm -rf $(B)

.PHONY: all flash isp clean
.SECONDARY:
