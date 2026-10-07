"""Exercise fresh customer configs and reciprocal Moscow bridge without secrets."""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path('/root/ArcVPN')))
import subscription_api as api

def exercise(profile, port, urls, parallel=1):
    profile['inbounds']=[{'listen':'127.0.0.1','port':port,'protocol':'socks','settings':{'auth':'noauth','udp':False}}]
    profile['log']={'loglevel':'none'}
    with tempfile.TemporaryDirectory(prefix='arc-se-delivery-') as folder:
        path=Path(folder)/'config.json';path.write_text(json.dumps(profile));path.chmod(0o600)
        proc=subprocess.Popen(['/tmp/arcvpn-canary-xray','run','-c',str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            time.sleep(5);responses=[]
            def request(item):
                url,expected=item
                cmd=['curl','-fsS','--max-time','20','--socks5-hostname',f'127.0.0.1:{port}']
                if expected=='204':cmd+=['-o','/dev/null','-w','%{http_code}']
                r=subprocess.run(cmd+[url],capture_output=True,text=True,timeout=25)
                if r.returncode or (expected=='204' and r.stdout.strip()!='204'):
                    raise RuntimeError('Tunnel request failed for '+profile.get('remarks','Moscow')+' status '+str(r.returncode))
                return r.stdout
            with ThreadPoolExecutor(max_workers=parallel) as pool:
                responses=list(pool.map(request,urls))
            return responses
        finally:proc.terminate();proc.wait(timeout=5)

def main():
    profiles=api._effective_customer_profiles()
    for profile in ([] if '--bridge-only' in sys.argv else profiles[:7]):
        exercise(profile,18610,[('https://www.gstatic.com/generate_204','204'),('https://www.youtube.com/generate_204','204')])
        print(json.dumps({'profile':profile['remarks'],'general':'passed','youtube':'passed'},ensure_ascii=False),flush=True)
    state=json.loads(Path('/root/ArcVPN/.secrets/sweden-remnawave-state.json').read_text())
    ru=json.loads(Path('/root/ArcVPN/.secrets/moscow-managed-bridge.json').read_text())
    bridge={'remarks':'Moscow bridge','outbounds':[{'tag':'proxy','protocol':'vless','settings':{'vnext':[
        {'address':'ru.arccnet.space','port':443,'users':[{'id':state['canary_user_uuid'],'encryption':'none','flow':'xtls-rprx-vision'}]}]},
        'streamSettings':{'network':'raw','security':'reality','realitySettings':{'serverName':'ru.arccnet.space',
            'fingerprint':'firefox','password':ru['ru_public_key'],'shortId':ru['ru_short_id']}}}]}
    bodies=exercise(bridge,18610,[('https://1.1.1.1/cdn-cgi/trace','trace') for _ in range(100)],parallel=5)
    counts={'SE':0,'EE':0}
    for body in bodies:
        ip=next(line[3:] for line in body.splitlines() if line.startswith('ip='))
        if ip=='136.148.220.228':counts['SE']+=1
        elif ip=='87.251.19.197':counts['EE']+=1
        else:raise RuntimeError('Unexpected Moscow bridge egress')
    if not all(counts.values()):raise RuntimeError('Both reciprocal paths not exercised')
    print(json.dumps({'moscow_bridge_egress':counts,'Finland':'absent'}),flush=True)

if __name__=='__main__':main()
