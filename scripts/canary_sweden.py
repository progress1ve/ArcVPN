"""Secret-free result for a temporary authenticated Sweden canary."""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

ROOT=Path('/root/ArcVPN')
XRAY='/tmp/arcvpn-canary-xray'

def main():
    state=json.loads((ROOT/'.secrets/sweden-remnawave-state.json').read_text())
    outbound={'tag':'proxy','protocol':'vless','settings':{'vnext':[{'address':'se.arccnet.space','port':443,
        'users':[{'id':state['canary_user_uuid'],'encryption':'none','flow':'xtls-rprx-vision'}]}]},
        'streamSettings':{'network':'raw','security':'reality','realitySettings':{'serverName':'se.arccnet.space',
            'fingerprint':'firefox','password':state['public_key'],'shortId':state['short_id']}}}
    config={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':18083,'protocol':'socks',
        'settings':{'auth':'noauth','udp':False}}],'outbounds':[outbound]}
    with tempfile.TemporaryDirectory(prefix='arc-se-canary-') as folder:
        path=Path(folder)/'config.json';path.write_text(json.dumps(config));path.chmod(0o600)
        syntax=subprocess.run([XRAY,'run','-test','-c',str(path)],capture_output=True)
        if syntax.returncode:raise RuntimeError('Canary syntax rejected')
        proc=subprocess.Popen([XRAY,'run','-c',str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            time.sleep(2)
            for name,url in [('general','https://www.gstatic.com/generate_204'),('youtube','https://www.youtube.com/generate_204')]:
                r=subprocess.run(['curl','-fsS','--max-time','25','--socks5-hostname','127.0.0.1:18083',
                    '-o','/dev/null','-w','%{http_code}',url],capture_output=True,text=True,timeout=30)
                if r.returncode or r.stdout.strip()!='204':raise RuntimeError(name+' tunnel failed: '+str(r.returncode)+' '+r.stdout.strip())
                print(json.dumps({'route':name,'tunnel':'passed','http':204}))
        finally:
            proc.terminate();proc.wait(timeout=5)

if __name__=='__main__':main()
