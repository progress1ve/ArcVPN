"""Bounded private Xray client gates; execute on Moscow with a trusted core."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

state = json.loads(Path('/opt/arcvpn/staging/estonia-fallback-canary.json').read_text())
root = Path(tempfile.mkdtemp(prefix='ee-tunnel-',dir='/opt/arcvpn/staging'))
os.chmod(root,0o700)
binary = '/opt/arcvpn/guide-canary/xray'
for index,name in enumerate(sys.argv[1:]):
    port = 19230 + index
    config = {'log':{'loglevel':'warning'},'inbounds':[{'tag':'socks','listen':'127.0.0.1','port':port,'protocol':'socks','settings':{'auth':'noauth','udp':True}}], 'outbounds':[state['outbounds'][name]]}
    path = root / (name+'.json')
    path.write_text(json.dumps(config))
    os.chmod(path,0o600)
    with (root/(name+'.log')).open('w') as log:
        process = subprocess.Popen([binary,'run','-c',str(path)],stdout=log,stderr=log)
        try:
            ready = False
            for _ in range(35):
                try:
                    with socket.create_connection(('127.0.0.1',port),timeout=.2): ready=True
                    break
                except OSError:
                    if process.poll() is not None:break
                    time.sleep(.1)
            if not ready:
                print(json.dumps({'route':name,'ready':False,'log_directory':str(root)}),flush=True)
                continue
            r = subprocess.run(['curl','-fsS','--max-time','16','--socks5-hostname',f'127.0.0.1:{port}','https://www.cloudflare.com/cdn-cgi/trace'],capture_output=True,text=True)
            values = dict(line.split('=',1) for line in r.stdout.splitlines() if '=' in line)
            print(json.dumps({'route':name,'ok':r.returncode==0,'trace':{k:values.get(k) for k in ('ip','loc','warp')},'error':r.stderr[-240:] if r.returncode else None,'log_directory':str(root) if r.returncode else None}),flush=True)
            if name in ('ordinary','warp'):
                target = 'https://www.youtube.com/generate_204' if name=='ordinary' else 'https://www.google.com/generate_204'
                r = subprocess.run(['curl','-sS','-o','/dev/null','-w','%{http_code}','--max-time','16','--socks5-hostname',f'127.0.0.1:{port}',target],capture_output=True,text=True)
                print(json.dumps({'route':name,'secondary_http':r.stdout,'ok':r.returncode==0 and r.stdout=='204'}),flush=True)
        finally:
            process.terminate()
            try:process.wait(timeout=4)
            except subprocess.TimeoutExpired: process.kill();process.wait()
