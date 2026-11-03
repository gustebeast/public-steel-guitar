#!/bin/bash
# The phone page on the Pi, from this checkout:  sudo bench/pi/phone/install.sh
# Names the Pi public-steel-guitar (avahi publishes public-steel-guitar.local), and runs
# server.py on port 80 as user psg from boot. docs/phone-ui.md.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
apt-get install -y avahi-daemon python3-serial
hostnamectl set-hostname public-steel-guitar
sed -i "s/127.0.1.1.*/127.0.1.1\tpublic-steel-guitar/" /etc/hosts
id psg >/dev/null 2>&1 || useradd --system --no-create-home --groups dialout psg
sed "s#^WorkingDirectory=.*#WorkingDirectory=$HERE#" "$HERE/../psg-phone.service" > /etc/systemd/system/psg-phone.service
systemctl daemon-reload
systemctl enable --now avahi-daemon psg-phone
systemctl restart avahi-daemon
echo "open http://public-steel-guitar.local on a phone on the same network"
