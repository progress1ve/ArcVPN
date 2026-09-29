"""Verify GET/header CDN traffic; never emit client credentials or Xray logs."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path('/root/ArcVPN')
sys.path.insert(0, str(ROOT))

def main():
    if os.environ.get('ARCVPN_CANARY_OUTBOUND'):
        outbound = json.loads(Path(os.environ['ARCVPN_CANARY_OUTBOUND']).read_text())
    else:
        from scripts.canary_single_cdn_xhttp import canary_outbound
        outbound = canary_outbound()
    xs = outbound['streamSettings']['xhttpSettings']
    xs.update({'uplinkHTTPMethod': 'GET', 'uplinkDataPlacement': 'header',
               'uplinkDataKey': 'X-Session-Token'})
    extra = xs.get('extra')
    if isinstance(extra, dict):
        extra.update({'uplinkHTTPMethod': 'GET', 'uplinkDataPlacement': 'header',
                      'uplinkDataKey': 'X-Session-Token'})
    xs['path'] = os.environ.get('ARCVPN_CANARY_PATH', '/api-test')
    target = outbound['settings']['vnext'][0]
    if os.environ.get('ARCVPN_CANARY_DIRECT'):
        target['address'] = os.environ['ARCVPN_CANARY_DIRECT']
        target['port'] = 80
        outbound['streamSettings']['security'] = 'none'
        outbound['streamSettings'].pop('tlsSettings', None)
    config = {'log': {'loglevel': 'none'}, 'inbounds': [{
        'listen': '127.0.0.1', 'port': 18083, 'protocol': 'socks',
        'settings': {'auth': 'noauth'}}], 'outbounds': [outbound]}
    with tempfile.TemporaryDirectory(prefix='arcvpn-get-') as tmp:
        path = Path(tmp) / 'config.json'
        path.write_text(json.dumps(config))
        path.chmod(0o600)
        process = subprocess.Popen([os.environ.get('ARCVPN_CANARY_XRAY', '/tmp/arcvpn-canary-xray'), 'run', '-c', str(path)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(2)
            result = subprocess.run(['curl', '-sS', '--max-time', '20',
                '--socks5-hostname', '127.0.0.1:18083', '-o', '/dev/null',
                '-w', '%{http_code}', 'https://www.google.com/generate_204'],
                capture_output=True, text=True, timeout=25)
            print(json.dumps({'path': xs['path'], 'curl': result.returncode,
                              'http': result.stdout, 'passed': result.stdout == '204'}))
        finally:
            process.terminate()
            process.wait(timeout=5)

if __name__ == '__main__':
    main()
