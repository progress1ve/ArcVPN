#!/bin/sh
set -eu
if [ "${RENEWED_LINEAGE:-}" = /etc/letsencrypt/live/ee.arccnet.space ]; then
    install -m 644 "$RENEWED_LINEAGE/fullchain.pem" /opt/remnanode/ssl/ee-public-fullchain.pem
    install -m 600 "$RENEWED_LINEAGE/privkey.pem" /opt/remnanode/ssl/ee-public-privkey.pem
fi
