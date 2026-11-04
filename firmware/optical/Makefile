# optical board bench firmware, built with the distribution's ARM GCC against TinyUSB and
# ST's HAL. Neither is in this repository: point TUSB at a checkout of
# https://github.com/hathach/tinyusb after `python3 tools/get_deps.py stm32h7` in it
# (the bench Pi has one at ~/src/tinyusb).
#
#   make            build/app/optical.elf and .bin, linked above the loader
#   make boot       the loader (boot.c), written once with the ST-LINK; it wipes nothing above
#                   its own sector
#   make usb        the application through the loader, over USB: usbflash.py
#   make rom        R2: the loader through ST's ROM over J1's CH340 (U32), no probe:
#                   bench/publicbench/romflash.py holds BOOT0 and pulses reset itself
#   make probe      the ST-LINK and the board through it, nothing written: the probe's
#                   firmware, the board's 3V3 as the probe reads it on TP5, the chip's ID
#   make flash      the application with openocd through the ST-LINK. It only runs through the
#                   loader, and the loader only starts it with a good record, so prefer make usb
#   make rescue     the same, holding the chip in reset (TP3) while connecting: for a
#                   chip whose firmware turns the debug pins off or sleeps
TUSB  ?= $(HOME)/src/tinyusb
HAL   := $(TUSB)/hw/mcu/st/stm32h7xx_hal_driver
DEV   := $(TUSB)/hw/mcu/st/cmsis_device_h7
BSP   := $(TUSB)/hw/bsp/stm32h7
CROSS ?= arm-none-eabi-
IMG   ?= app
B     := build/$(IMG)

HALSRC := hal hal_cortex hal_dma hal_gpio hal_pwr hal_pwr_ex hal_rcc hal_rcc_ex hal_sai hal_sai_ex \
          hal_flash hal_flash_ex
ifeq ($(IMG),boot)
FIRST := boot.c
PID   := 0x4007
LD    := $(BSP)/linker/stm32h743xx_flash.ld
VECT  :=
else
FIRST := main.c
PID   := 0x4006
LD    := $(B)/app.ld
VECT  := -DUSER_VECT_TAB_ADDRESS -DVECT_TAB_OFFSET=0x40000U
endif
SRC := $(FIRST) board.c $(B)/usb_descriptors.c \
       $(TUSB)/src/tusb.c $(TUSB)/src/common/tusb_fifo.c \
       $(TUSB)/src/device/usbd.c \
       $(TUSB)/src/class/cdc/cdc_device.c \
       $(TUSB)/src/portable/synopsys/dwc2/dcd_dwc2.c $(TUSB)/src/portable/synopsys/dwc2/dwc2_common.c \
       $(DEV)/Source/Templates/system_stm32h7xx.c \
       $(patsubst %,$(HAL)/Src/stm32h7xx_%.c,$(HALSRC))
OBJ := $(patsubst %.c,$(B)/%.o,$(notdir $(SRC))) $(B)/startup.o

CFLAGS := -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard -Os -g \
          -ffunction-sections -fdata-sections -fno-common -Wall \
          -DSTM32H743xx -DHSE_VALUE=25000000 $(VECT) \
          -I. -I$(B) -I$(TUSB)/src -I$(TUSB)/hw -I$(HAL)/Inc -I$(DEV)/Include \
          -I$(TUSB)/lib/CMSIS_5/CMSIS/Core/Include
LDFLAGS := -T$(LD) -nostartfiles --specs=nano.specs --specs=nosys.specs \
           -Wl,--gc-sections -Wl,-Map,$(B)/optical.map

all: $(B)/optical.bin
	$(CROSS)size $(B)/optical.elf

boot:
	$(MAKE) IMG=boot all
	$(OCD) -c "program build/boot/optical.elf verify reset exit"

rom:
	$(MAKE) IMG=boot build/boot/optical.bin
	PYTHONPATH=$(CURDIR)/../../bench python3 -m publicbench.romflash optical build/boot/optical.bin

usb: $(B)/optical.bin
	python3 ../output_panel/usbflash.py --ids cafe:4007,cafe:4006 --app 0x40000 --page 4096 $<

$(B)/optical.bin: $(B)/optical.elf
	$(CROSS)objcopy -O binary $< $@

# TinyUSB's two-port descriptors, under this image's id, so the Pi can tell which is running
$(B)/usb_descriptors.c: $(TUSB)/examples/device/cdc_dual_ports/src/usb_descriptors.c
	mkdir -p $(B)
	sed 's/#define USB_PID .*/#define USB_PID $(PID)/' $< > $@

$(B)/app.ld: $(BSP)/linker/stm32h743xx_flash.ld
	mkdir -p $(B)
	sed 's/ORIGIN = 0x08000000, LENGTH = 2048K/ORIGIN = 0x08040000, LENGTH = 768K/' $< > $@

vpath %.c $(sort $(dir $(SRC)))

# ST's HAL wants a configuration header; TinyUSB's own, with the SAI turned on
$(B)/stm32h7xx_hal_conf.h: $(BSP)/stm32h7xx_hal_conf.h
	mkdir -p $(B)
	sed 's|/\* *#define HAL_SAI_MODULE_ENABLED *\*/|#define HAL_SAI_MODULE_ENABLED|' $< > $@

$(B)/%.o: %.c $(B)/stm32h7xx_hal_conf.h tusb_config.h board.h
	$(CROSS)gcc $(CFLAGS) -c $< -o $@

$(B)/startup.o: $(DEV)/Source/Templates/gcc/startup_stm32h743xx.s $(B)/stm32h7xx_hal_conf.h
	$(CROSS)gcc $(CFLAGS) -c $< -o $@

$(B)/optical.elf: $(OBJ) $(LD)
	$(CROSS)gcc $(CFLAGS) $(OBJ) $(LDFLAGS) -o $@
	@test "$(IMG)" != boot || test $$($(CROSS)size $@ | awk 'END{print $$1+$$2}') -lt 131072

# (the ST-LINK/V2 on the bench Pi, firmware V2J46S7, runs SWD directly: `transport select`
# says so rather than leaving openocd to guess and warn)
OCD := openocd -f interface/stlink.cfg -c "transport select swd" -f target/stm32h7x.cfg

probe:
	st-info --probe
	$(OCD) -c "init; targets; exit"

flash: $(B)/optical.elf
	$(OCD) -c "program $< verify reset exit"

rescue: $(B)/optical.elf
	$(OCD) -c "reset_config srst_only srst_nogate connect_assert_srst" -c "program $< verify reset exit"

clean:
	rm -rf $(B)

.PHONY: all boot usb rom probe flash rescue clean
