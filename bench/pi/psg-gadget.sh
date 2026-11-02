#!/bin/bash
# The Pi's USB-C as a device, through output_panel J2 and its panel socket to the computer:
# one serial port for now, /dev/ttyGS0 here. MIDI, audio and DFU join this composite later.
# The lead's VBUS is open on purpose, so nothing here may wait on it.
set -e
modprobe libcomposite
G=/sys/kernel/config/usb_gadget/psg
if [ "$1" = stop ]; then
    echo "" > "$G/UDC" || true
    rm -f "$G/configs/c.1/acm.usb0"
    rmdir "$G/configs/c.1/strings/0x409" "$G/configs/c.1" "$G/functions/acm.usb0" "$G/strings/0x409" "$G"
    exit 0
fi
mkdir -p "$G"
echo 0xcafe > "$G/idVendor"
echo 0x4010 > "$G/idProduct"
echo 0x0100 > "$G/bcdDevice"
echo 0x0200 > "$G/bcdUSB"
mkdir -p "$G/strings/0x409" "$G/configs/c.1/strings/0x409" "$G/functions/acm.usb0"
echo "Public Steel Guitar" > "$G/strings/0x409/manufacturer"
echo "PSG Pi" > "$G/strings/0x409/product"
echo "psg" > "$G/configs/c.1/strings/0x409/configuration"
echo 100 > "$G/configs/c.1/MaxPower"
ln -sf "$G/functions/acm.usb0" "$G/configs/c.1/"
for _ in $(seq 100); do
    u=$(ls /sys/class/udc | head -1)
    [ -n "$u" ] && break
    sleep 0.1
done
echo "$u" > "$G/UDC"
