#!/usr/bin/env bash
set -euo pipefail

JAIL_LOCAL="/etc/fail2ban/jail.d/zumbot-nginx.local"
FILTER_LOCAL="/etc/fail2ban/filter.d/nginx-zumbot-scanners.conf"
LOG_PATH="/var/log/nginx/access.log"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "[FAIL] run as root"
  exit 1
fi

if ! command -v fail2ban-server >/dev/null 2>&1; then
  echo "[INFO] fail2ban not found, installing..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y fail2ban
fi

mkdir -p /etc/fail2ban/jail.d /etc/fail2ban/filter.d

cat > "${FILTER_LOCAL}" <<'FILTER'
[Definition]
# Бан по scanner path и HTTP 444/403 в nginx access.log
failregex = ^<HOST> - .*"(?:GET|POST|HEAD|OPTIONS) /(wp-admin|wp-login\.php|\.env|phpmyadmin|cgi-bin|vendor|actuator|\.git|boaform|HNAP1).*" (?:403|404|444) .*$
ignoreregex =
FILTER

cat > "${JAIL_LOCAL}" <<JAIL
[nginx-zumbot-scanners]
enabled = true
port = http,https
filter = nginx-zumbot-scanners
logpath = ${LOG_PATH}
maxretry = 8
findtime = 10m
bantime = 1h
backend = auto

[nginx-badbots]
enabled = true
port = http,https
logpath = ${LOG_PATH}
maxretry = 3
findtime = 10m
bantime = 1h
backend = auto
JAIL

systemctl enable fail2ban >/dev/null
systemctl restart fail2ban

echo "[OK] fail2ban configured"
fail2ban-client status
