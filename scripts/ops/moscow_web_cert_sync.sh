#!/bin/sh
set -eu
install -m 644 /etc/letsencrypt/live/arccnet.space/fullchain.pem /etc/arcvpn-web-tls/fullchain.pem
install -m 600 /etc/letsencrypt/live/arccnet.space/privkey.pem /etc/arcvpn-web-tls/privkey.pem
nginx -t
systemctl reload nginx
