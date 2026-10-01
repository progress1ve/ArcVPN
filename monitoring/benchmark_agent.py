#!/usr/bin/env python3
"""One allowlisted, pinned benchmark; no network script downloads or installs."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import urllib.request

SHA = "068d37703beab0ec7e44a24ed45f6e911af51511ea6476a85add7250fab3d3dc"


def main():
    configuration = json.loads(Path('/etc/arcvpn/benchmark-agent.json').read_text())
    def request(payload):
        req = urllib.request.Request('https://arccnet.space/api/internal/benchmark-agent',
            data=json.dumps(payload).encode(), headers={'Content-Type':'application/json',
            'Authorization':'Bearer ' + configuration['token']})
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.load(response)
    response = request({'action':'claim', 'host':configuration['host']})
    job = response.get('job')
    if not job:
        return
    source = Path('/usr/local/lib/arcvpn/russian-iperf3.sh')
    if hashlib.sha256(source.read_bytes()).hexdigest() != SHA:
        request({'action':'update','id':job['id'],'host':configuration['host'],
                 'status':'failed','output':'Pinned source checksum mismatch','exit_code':126})
        return
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(['/bin/bash',str(source),'--debug'], stdin=subprocess.DEVNULL,
            stdout=output,stderr=subprocess.STDOUT,start_new_session=True,
            env={'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C.UTF-8'})
        started = time.monotonic()
        state = 'running'
        try:
            while process.poll() is None:
                time.sleep(5)
                log = os.pread(output.fileno(),100000,0).decode('utf-8','replace')
                response = request({'action':'update','id':job['id'],'host':configuration['host'],
                                    'status':'running','output':log})
                if response.get('cancel') or time.monotonic()-started > 900:
                    state = 'cancelled' if response.get('cancel') else 'failed'
                    os.killpg(process.pid,signal.SIGTERM)
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL)
                    break
        finally:
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGKILL)
            process.wait()
        log = os.pread(output.fileno(),100000,0).decode('utf-8','replace')
        request({'action':'update','id':job['id'],'host':configuration['host'],
                 'status':state if state != 'running' else 'completed' if process.returncode == 0 else 'failed',
                 'output':log,'exit_code':process.returncode})


if __name__ == '__main__':
    main()
