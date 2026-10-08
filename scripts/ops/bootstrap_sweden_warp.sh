#!/usr/bin/env bash
set -euo pipefail
# Official Cloudflare repository; proxy mode leaves host routes unchanged.
if ! command -v warp-cli >/dev/null; then
  curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
  release=$(. /etc/os-release; echo "$VERSION_CODENAME")
  printf 'deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ %s main\n' "$release" > /etc/apt/sources.list.d/cloudflare-client.list
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq cloudflare-warp
fi
systemctl enable --now warp-svc
warp-cli --version
warp-cli proxy --help
