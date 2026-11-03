#!/bin/bash
# The phone page on the Pi, from this checkout:  sudo bench/pi/phone/install.sh
# Names the Pi public-steel-guitar (avahi publishes public-steel-guitar.local), and runs
# server.py (a copy, in /opt/public-steel-guitar) on ports 80 and 443, as you, from boot. docs/phone-ui.md.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
apt-get install -y avahi-daemon python3-serial openssl
hostnamectl set-hostname public-steel-guitar
sed -i "s/127.0.1.1.*/127.0.1.1\tpublic-steel-guitar/" /etc/hosts
# It runs as YOU (the sudo user), the user the bench scripts run as: it has to see which
# process holds the motor port before it opens it, and Linux hides other users' open files.
U="${SUDO_USER:?run it with sudo from your own account}"
usermod -aG dialout "$U"
# HTTPS: a CA made here, once, and a server certificate from it for every name the Pi
# answers to. Install the CA on the phone (http://public-steel-guitar.home/ca.crt) and the
# page loads with no warning. docs/phone-ui.md.
T=/var/lib/public-steel-guitar-phone/tls
if [ ! -f "$T/server.crt" ]; then
  mkdir -p "$T"
  openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -subj "/CN=public-steel-guitar local CA" \
    -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -keyout "$T/ca.key" -out "$T/ca.crt"
  SAN="DNS:public-steel-guitar.home,DNS:public-steel-guitar.local,DNS:public-steel-guitar"
  for ip in $(hostname -I); do case $ip in *:*) ;; *) SAN="$SAN,IP:$ip" ;; esac; done
  openssl req -newkey rsa:2048 -nodes -subj "/CN=public-steel-guitar.home" \
    -keyout "$T/server.key" -out "$T/server.csr"
  printf 'subjectAltName=%s\nextendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\n' \
    "$SAN" > "$T/ext.cnf"
  # 825 days: the longest a phone accepts for a server certificate
  openssl x509 -req -in "$T/server.csr" -CA "$T/ca.crt" -CAkey "$T/ca.key" -CAcreateserial \
    -days 825 -extfile "$T/ext.cnf" -out "$T/server.crt"
  rm -f "$T/server.csr" "$T/ext.cnf"
  chmod 600 "$T"/*.key
fi
chown -R "$U" "$T"
# The service runs a copy in /opt, so an edit in the checkout cannot take it down mid-use.
# Run this again after changing anything in bench/.
APP=/opt/public-steel-guitar/bench
mkdir -p "$(dirname "$APP")"
rm -rf "$APP"
cp -r "$HERE/../.." "$APP"
sed "s/^User=.*/User=$U/" "$HERE/../public-steel-guitar-phone.service" > /etc/systemd/system/public-steel-guitar-phone.service
systemctl daemon-reload
systemctl enable avahi-daemon public-steel-guitar-phone
systemctl restart public-steel-guitar-phone
systemctl restart avahi-daemon
echo "open https://public-steel-guitar.home on a phone on the same network (CA: http://public-steel-guitar.home/ca.crt)"
