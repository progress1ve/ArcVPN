"""Remote-only bounded node comparison; private profiles enter via a mode0600 file.

No Telegram account, session, browser or media cache is used. Public HTTPS media
ranges and unauthenticated fresh MTProto handshakes are distinct measurements.
"""
import argparse
import copy
import hashlib
import html
import json
import os
from pathlib import Path
import re
import secrets
import socket
import statistics
import struct
import subprocess
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

DC = {'dc1': '149.154.175.50', 'dc2': '149.154.167.51',
      'dc3': '149.154.175.100', 'dc4': '149.154.167.91',
      'dc5': '91.108.56.130'}
NAMES = {'A': '🇳🇱 Тест A', 'B': '🇳🇱 Тест B',
         'NL': '🇳🇱 Нидерланды', 'LT': '🇱🇹 Литва'}
MARKER = b'\nARCVPN_METRICS\n'
CHUNK = 3 * 1024 * 1024


def recv_exact(sock, size):
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise EOFError('short packet')
        data.extend(chunk)
    return bytes(data)


def mtproto(port, ip):
    started = time.monotonic()
    with socket.create_connection(('127.0.0.1', port), timeout=8) as sock:
        sock.settimeout(8)
        sock.sendall(b'\x05\x01\x00')
        if recv_exact(sock, 2) != b'\x05\x00':
            raise ValueError('SOCKS auth')
        sock.sendall(b'\x05\x01\x00\x01' + socket.inet_aton(ip) + struct.pack('!H', 443))
        reply = recv_exact(sock, 4)
        if reply[:2] != b'\x05\x00':
            raise ValueError('SOCKS connect')
        address_size = {1: 4, 4: 16}.get(reply[3])
        if reply[3] == 3:
            address_size = recv_exact(sock, 1)[0]
        if address_size is None:
            raise ValueError('SOCKS address')
        recv_exact(sock, address_size + 2)
        nonce = secrets.token_bytes(16)
        body = struct.pack('<I', 0xbe7e8ef1) + nonce
        message = struct.pack('<QQI', 0, (time.time_ns() * (1 << 32) // 10**9) & ~3,
                              len(body)) + body
        sock.sendall(b'\xee' * 4 + struct.pack('<I', len(message)) + message)
        size = struct.unpack('<I', recv_exact(sock, 4))[0]
        if not 40 <= size <= 4096:
            raise ValueError('MTProto frame length')
        answer = recv_exact(sock, size)
        if (answer[:8] != bytes(8) or answer[20:24] != struct.pack('<I', 0x05162463)
                or answer[24:40] != nonce
                or struct.unpack('<I', answer[16:20])[0] != len(answer) - 20):
            raise ValueError('MTProto nonce or envelope')
    return round((time.monotonic() - started) * 1000, 2)


def curl(port, url, *, offset=None, ip=None, header_path=None, head=False):
    command = ['curl', '-sS', '--noproxy', '', '--connect-timeout', '8',
               '--max-time', '25', '--http1.1', '--socks5', f'127.0.0.1:{port}',
               '--config', '-', '-w', '\nARCVPN_METRICS\n%{json}']
    if head:
        command += ['-I']
    if offset is not None:
        command += ['--range', f'{offset}-{offset + CHUNK - 1}',
                    '-H', 'Cache-Control: no-cache', '-H', 'Pragma: no-cache']
    if ip:
        command += ['--resolve', f'{urlsplit(url).hostname}:443:{ip}']
    if header_path:
        command += ['-D', str(header_path)]
    result = subprocess.run(command, input=('url = ' + json.dumps(url) + '\n').encode(),
                            capture_output=True, timeout=30)
    raw, _, metadata = result.stdout.rpartition(MARKER)
    if not metadata:
        return b'', {'ok': False, 'curl_exit': result.returncode}
    data = json.loads(metadata)
    return raw, {'ok': result.returncode == 0, 'curl_exit': result.returncode,
                 'http': data['http_code'], 'bytes': int(data['size_download']),
                 'first_ms': round(data['time_starttransfer'] * 1000, 2),
                 'total_ms': round(data['time_total'] * 1000, 2),
                 'tcp_ms': round(data['time_connect'] * 1000, 2),
                 'tls_ms': round(data['time_appconnect'] * 1000, 2)}


def discover_video():
    with urlopen('https://t.me/s/telegram', timeout=15) as response:
        page = response.read().decode()
    for value in re.findall(r'<video[^>]+src="([^"]+)"', page)[:12]:
        url = html.unescape(value)
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname.endswith('.telesco.pe'):
            continue
        try:
            with urlopen(Request(url, method='HEAD'), timeout=10) as response:
                size = int(response.headers.get('Content-Length', 0))
                if size >= 7 * 1024 * 1024:
                    return url, size
        except (OSError, ValueError):
            continue
    raise RuntimeError('No suitable public Telegram video')


def stats(values):
    if not values:
        return None
    ordered = sorted(values)
    return {'n': len(values), 'median': round(statistics.median(ordered), 2),
            'p95': ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)],
            'max': ordered[-1]}


def run(args):
    if args.profiles.stat().st_mode & 0o077:
        raise RuntimeError('Private profiles must be mode0600')
    profiles = json.loads(args.profiles.read_text())
    version = subprocess.check_output([str(args.xray), 'version'], text=True).splitlines()[0]
    report = {'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'xray': version, 'source_route': subprocess.check_output(
                  ['ip', '-4', 'route', 'get', '45.141.202.248'], text=True).strip(),
              'mtproto': [], 'media': [], 'egress': {}}
    children, ports = [], {}
    try:
        with tempfile.TemporaryDirectory(prefix='arc-remote-node-ab-') as directory:
            root = Path(directory)
            for label, name in NAMES.items():
                config = copy.deepcopy(next(p for p in profiles if p.get('remarks') == name))
                with socket.socket() as sock:
                    sock.bind(('127.0.0.1', 0))
                    port = sock.getsockname()[1]
                config['inbounds'] = [{'listen': '127.0.0.1', 'port': port,
                                       'protocol': 'socks', 'settings': {'auth': 'noauth'}}]
                config['log'] = {'loglevel': 'none'}
                path = root / (label + '.json')
                path.write_text(json.dumps(config)); path.chmod(0o600)
                check = subprocess.run([str(args.xray), 'run', '-test', '-c', str(path)],
                                       capture_output=True)
                if check.returncode:
                    raise RuntimeError('Client configuration rejected: ' + label)
                children.append(subprocess.Popen([str(args.xray), 'run', '-c', str(path)],
                                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
                ports[label] = port
            time.sleep(.5)
            for label, port in ports.items():
                data, result = curl(port, 'https://www.cloudflare.com/cdn-cgi/trace')
                fields = dict(x.split('=', 1) for x in data.decode().splitlines() if '=' in x)
                expected = '88.216.62.135' if label == 'LT' else '45.141.202.248'
                if not result['ok'] or fields.get('ip') != expected:
                    raise RuntimeError('Unexpected egress: ' + label)
                report['egress'][label] = fields['ip']
            for round_id in range(6):
                order = ['A', 'B', 'NL', 'LT'] if round_id % 2 == 0 else ['LT', 'NL', 'B', 'A']
                for dc, ip in DC.items():
                    for label in order:
                        row = {'round': round_id, 'route': label, 'dc': dc}
                        try:
                            row.update(ok=True, ms=mtproto(ports[label], ip))
                        except (OSError, EOFError, ValueError) as error:
                            row.update(ok=False, error=type(error).__name__)
                        report['mtproto'].append(row)
                print(json.dumps({'phase': 'mtproto', 'round': round_id + 1}), flush=True)
            url, size = discover_video()
            host = urlsplit(url).hostname
            ip = socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
            report['object'] = {'host': host, 'total_bytes': size, 'client_target_ip': ip,
                                'public_channel': 'telegram', 'path_logged': False,
                                'local_media_cache': False, 'server_cache': 'uncontrolled'}
            offsets = [0, ((size - CHUNK) // 2 // 4096) * 4096, size - CHUNK]
            hashes = {}
            for index, offset in enumerate(offsets):
                for repeat, order in enumerate((['A', 'B', 'NL', 'LT'], ['LT', 'NL', 'B', 'A'])):
                    for label in order:
                        headers = root / 'headers'
                        payload, row = curl(ports[label], url, offset=offset, ip=ip, header_path=headers)
                        text = headers.read_text() if headers.exists() else ''
                        fields = {}
                        for line in text.splitlines():
                            if ':' in line:
                                key, value = line.split(':', 1); fields[key.lower()] = value.strip()
                        digest = hashlib.sha256(payload).hexdigest()
                        valid = (row['ok'] and row['http'] == 206 and len(payload) == CHUNK
                                 and fields.get('content-range') == f'bytes {offset}-{offset+CHUNK-1}/{size}')
                        if valid:
                            hashes.setdefault(offset, digest)
                            valid = hashes[offset] == digest
                        row.update(route=label, range_index=index, repeat=repeat, offset=offset,
                                   ok=valid, payload_bytes=len(payload), same_bytes=valid,
                                   cache={k: fields[k] for k in ('age', 'x-cache', 'cf-cache-status', 'cache-control')
                                          if k in fields})
                        report['media'].append(row)
                        del payload
                    print(json.dumps({'phase': 'media', 'range': index, 'repeat': repeat}), flush=True)
    finally:
        for child in children:
            child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait()
        args.profiles.unlink(missing_ok=True)
        report['summary'] = {}
        for label in NAMES:
            nonce = [r for r in report['mtproto'] if r['route'] == label]
            media = [r for r in report['media'] if r['route'] == label]
            report['summary'][label] = {
                'mtproto_ok': sum(r['ok'] for r in nonce), 'mtproto_total': len(nonce),
                'mtproto_ms': stats([r['ms'] for r in nonce if r['ok']]),
                'media_ok': sum(r['ok'] for r in media), 'media_total': len(media),
                'media_first_ms': stats([r['first_ms'] for r in media if r['ok']]),
                'media_total_ms': stats([r['total_ms'] for r in media if r['ok']])}
        report['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps({'summary': report['summary'], 'cleanup': 'clients stopped, credentials removed'}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--profiles', type=Path, required=True)
    parser.add_argument('--xray', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args())
