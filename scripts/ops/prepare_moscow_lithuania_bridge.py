"""Add TCP AI and UDP Hysteria forwarding to the existing Moscow bridge."""
import os
import shutil
import subprocess
from pathlib import Path

def run(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)

haproxy = Path('/etc/haproxy/haproxy.cfg')
backup = Path('/root/arcvpn-youtube-before-20261027/haproxy-before-lt-global.cfg')
original = haproxy.read_text()
if not backup.exists():
    shutil.copy2(haproxy, backup)
assert 'arcvpn_lt_owner_bridge' in original, 'Existing TCP LT bridge is required'
if 'arcvpn_lt_ai_bridge' not in original:
    haproxy.write_text(original + '''
frontend arcvpn_lt_ai_bridge
    bind *:9444
    mode tcp
    default_backend arcvpn_lt_ai_exit
backend arcvpn_lt_ai_exit
    mode tcp
    server lithuania 88.216.62.135:8444 check
''')
try:
    run('haproxy', '-c', '-f', str(haproxy))
except Exception:
    haproxy.write_text(original)
    raise

nftfile = Path('/etc/arcvpn-lt-game.nft')
nftfile.write_text('''table ip arcvpn_lt_game {
 chain prerouting {
  type nat hook prerouting priority dstnat; policy accept;
  ip daddr 95.182.120.237 udp dport 443 dnat to 88.216.62.135:443
 }
 chain postrouting {
  type nat hook postrouting priority srcnat; policy accept;
  ip daddr 88.216.62.135 udp dport 443 masquerade
 }
}
''')
run('nft', '-c', '-f', str(nftfile))
unit = Path('/etc/systemd/system/arcvpn-lt-game-forward.service')
unit.write_text('''[Unit]
Description=ArcVPN scoped UDP game bridge to Lithuania
After=network-online.target ufw.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/nft -f /etc/arcvpn-lt-game.nft
ExecStop=/usr/sbin/nft delete table ip arcvpn_lt_game

[Install]
WantedBy=multi-user.target
''')
run('ufw', 'allow', '9444/tcp')
run('ufw', 'route', 'allow', 'proto', 'udp', 'to', '88.216.62.135', 'port', '443')
run('systemctl', 'daemon-reload')
if subprocess.run(['nft', 'list', 'table', 'ip', 'arcvpn_lt_game'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
    run('systemctl', 'enable', '--now', 'arcvpn-lt-game-forward.service')
run('systemctl', 'reload', 'haproxy')
print('Moscow AI TCP and Lithuania game UDP forwarding configured')
