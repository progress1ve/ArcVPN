"""Run on Royale. Creates a 24-hour standalone TCP tuning experiment, prints no credentials."""
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import time
from uuid import uuid4

ROOT = Path('/usr/local/lib/arcvpn-reality-tcp-test')
PRIVATE = Path('/etc/arcvpn/reality-tcp-test')
UNIT = Path('/etc/systemd/system/arcvpn-reality-tcp-test.service')
PORT_SETTINGS = {
    9443: {'tcpcongestion': 'cubic'},
    9445: {'tcpcongestion': 'bbr'},
}
PORTS = tuple(PORT_SETTINGS)


def run(*args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'{args[0]} failed with exit {result.returncode}')
    return result.stdout


def private_file(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream)


def main():
    assert os.geteuid() == 0
    assert not ROOT.exists() and not PRIVATE.exists() and not UNIT.exists()
    assert not Path('/run/systemd/transient/arcvpn-reality-tcp-test-expiry.timer').exists()
    listeners = run('ss', '-H', '-lnt')
    firewall = run('ufw', 'status')
    assert 'Status: active' in firewall
    assert all(not re.search(rf':{port}\b', listeners) and str(port) not in firewall
               for port in PORTS)
    ROOT.mkdir(mode=0o755)
    ROOT.chmod(0o755)
    PRIVATE.mkdir(mode=0o700, parents=True)
    pid = run('docker', 'inspect', '--format', '{{.State.Pid}}', 'remnanode').strip()
    binary = run('docker', 'exec', 'remnanode', 'sh', '-c', 'command -v xray').strip()
    assets = run('docker', 'exec', 'remnanode', 'sh', '-c',
                 'for d in /usr/local/share/xray /usr/local/bin /etc/xray; do '
                 'if [ -s "$d/geoip.dat" ] && [ -s "$d/geosite.dat" ]; then '
                 'printf "%s" "$d"; break; fi; done').strip()
    assert assets and binary.startswith('/')
    container = Path('/proc') / pid / 'root'
    shutil.copyfile(container / binary.lstrip('/'), ROOT / 'xray')
    (ROOT / 'xray').chmod(0o755)
    for name in ('geoip.dat', 'geosite.dat'):
        shutil.copyfile(container / assets.lstrip('/') / name, ROOT / name)
        (ROOT / name).chmod(0o644)
    keys = run(str(ROOT / 'xray'), 'x25519')
    private = re.search(r'(?im)^Private\s*key:\s*(\S+)', keys).group(1)
    public = re.search(r'(?im)^(?:Password[^:]*|Public\s*key):\s*(\S+)', keys).group(1)
    identity, short_id = str(uuid4()), secrets.token_hex(8)
    expires = int(time.time()) + 86400
    inbounds = []
    for port, socket_options in PORT_SETTINGS.items():
        inbounds.append({
            'tag': 'owner-ab-' + str(port), 'listen': '0.0.0.0', 'port': port,
            'protocol': 'vless', 'settings': {'decryption': 'none', 'clients': [
                {'id': identity, 'flow': 'xtls-rprx-vision'}]},
            'sniffing': {'enabled': True, 'routeOnly': False,
                         'destOverride': ['http', 'tls', 'quic']},
            'streamSettings': {'network': 'raw', 'security': 'reality',
                'sockopt': socket_options,
                'realitySettings': {'target': '127.0.0.1:8443', 'xver': 0,
                    'serverNames': ['nl.arccnet.space'], 'privateKey': private,
                    'shortIds': [short_id]}},
        })
    config = {'log': {'loglevel': 'none'}, 'dns': {'servers': ['1.1.1.1', '1.0.0.1']},
              'inbounds': inbounds,
              'outbounds': [{'tag': 'DIRECT', 'protocol': 'freedom'},
                            {'tag': 'BLOCK', 'protocol': 'blackhole'}],
              'routing': {'rules': [
                  {'type': 'field', 'ip': ['geoip:private'], 'outboundTag': 'BLOCK'},
                  {'type': 'field', 'domain': ['geosite:private'], 'outboundTag': 'BLOCK'},
                  {'type': 'field', 'protocol': ['bittorrent'], 'outboundTag': 'BLOCK'},
              ]}}
    private_file(PRIVATE / 'server.json', config)
    private_file(PRIVATE / 'client.json', {'enabled': True, 'expires_at': expires,
                 'experiment': 'tcp-tuning', 'uuid': identity, 'public_key': public, 'short_id': short_id})
    env = {**os.environ, 'XRAY_LOCATION_ASSET': str(ROOT)}
    validation = subprocess.run([str(ROOT / 'xray'), 'run', '-test', '-config',
                                 str(PRIVATE / 'server.json')], env=env, capture_output=True)
    assert validation.returncode == 0, 'canary config validation failed'
    UNIT.write_text('''[Unit]
Description=ArcVPN owner TCP tuning (24 hours)
After=network-online.target
[Service]
Type=simple
DynamicUser=yes
LoadCredential=config.json:/etc/arcvpn/reality-tcp-test/server.json
ExecStart=/usr/local/lib/arcvpn-reality-tcp-test/xray run -config %d/config.json
Environment=XRAY_LOCATION_ASSET=/usr/local/lib/arcvpn-reality-tcp-test
RuntimeMaxSec=24h
Restart=no
CPUQuota=25%
MemoryMax=192M
TasksMax=64
LimitNOFILE=4096
NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
CapabilityBoundingSet=
''')
    cleanup = ROOT / 'expire.sh'
    cleanup.write_text('''#!/bin/sh
systemctl stop arcvpn-reality-tcp-test.service
ufw --force delete allow 9443/tcp >/dev/null 2>&1 || true
ufw --force delete allow 9445/tcp >/dev/null 2>&1 || true
rm -f /etc/arcvpn/reality-tcp-test/server.json /etc/arcvpn/reality-tcp-test/client.json
''')
    cleanup.chmod(0o700)
    opened = []
    try:
        run('modprobe', 'tcp_bbr')
        assert 'bbr' in run('sysctl', '-n', 'net.ipv4.tcp_available_congestion_control').split()
        run('systemctl', 'daemon-reload')
        for port in PORTS:
            run('ufw', 'allow', f'{port}/tcp', 'comment', 'arcvpn-reality-tcp-test')
            opened.append(port)
        run('systemctl', 'start', 'arcvpn-reality-tcp-test.service')
        run('systemd-run', '--unit=arcvpn-reality-tcp-test-expiry', '--on-active=24h',
            '--timer-property=AccuracySec=1s', str(cleanup))
        assert run('systemctl', 'is-active', 'arcvpn-reality-tcp-test.service').strip() == 'active'
        print(json.dumps({'ports': PORTS, 'expires_at': expires, 'service': 'active'}))
    except Exception:
        subprocess.run(['systemctl', 'stop', 'arcvpn-reality-tcp-test.service'], capture_output=True)
        for port in opened:
            subprocess.run(['ufw', '--force', 'delete', 'allow', f'{port}/tcp'], capture_output=True)
        raise


if __name__ == '__main__':
    main()
