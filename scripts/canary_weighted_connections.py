"""Exercise real Xray weighted routing, healthy peers and both failure states."""
import json
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
try:
    from monitoring.weighted_connections import configure
except ModuleNotFoundError:
    from weighted_connections import configure

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith('generate_204'):
            self.send_response(204); self.end_headers(); return
        body=self.server.country.encode()
        self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass

def main():
    servers=[]
    for port,country in [(18601,'SE'),(18602,'EE')]:
        server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.country=country
        threading.Thread(target=server.serve_forever,daemon=True).start();servers.append(server)
    profile={'log':{'loglevel':'none'},'inbounds':[{'listen':'127.0.0.1','port':18603,'protocol':'socks','settings':{'auth':'noauth'}}],
        'outbounds':[{'tag':country,'protocol':'freedom','settings':{'redirect':f'127.0.0.1:{port}'}} for port,country in [(18601,'SE'),(18602,'EE')]]+[
            {'tag':'block','protocol':'blackhole'}],
        'observatory':{'subjectSelector':['SE','EE'],'probeURL':'http://127.0.0.1/generate_204','probeInterval':'1s','enableConcurrency':True},
        'routing':{'balancers':[{'tag':'main'}],'rules':[{'type':'field','network':'tcp','balancerTag':'main'}]}}
    configure(profile,profile['routing']['balancers'][0],[('SE',61),('EE',39)])
    def request():
        r=subprocess.run(['curl','-fsS','--max-time','2','--socks5-hostname','127.0.0.1:18603','http://127.0.0.1/data'],capture_output=True,text=True)
        return r.stdout.strip() if r.returncode==0 else 'failed'
    with tempfile.TemporaryDirectory(prefix='arc-weight-canary-') as folder:
        path=Path(folder)/'config.json';path.write_text(json.dumps(profile))
        syntax=subprocess.run(['/tmp/arcvpn-canary-xray','run','-test','-c',str(path)],capture_output=True)
        if syntax.returncode:raise RuntimeError('Weighted Xray syntax failed')
        process=subprocess.Popen(['/tmp/arcvpn-canary-xray','run','-c',str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            time.sleep(4);counts={'SE':0,'EE':0,'failed':0}
            for _ in range(500):counts[request()]+=1
            if counts['failed'] or not 255 <= counts['SE'] <= 355:raise RuntimeError('Weighted distribution failed '+str(counts))
            servers[0].shutdown();servers[0].server_close();time.sleep(4)
            if any(request()!='EE' for _ in range(30)):raise RuntimeError('SE-down fallback failed')
            servers[1].shutdown();servers[1].server_close();time.sleep(4)
            if any(request()!='failed' for _ in range(3)):raise RuntimeError('Both-down did not fail closed')
            print(json.dumps({'weighted_connections':counts,'se_down':'EE passed','both_down':'blocked'}))
        finally:process.terminate();process.wait(timeout=5)
    for server in servers:server.server_close()

if __name__=='__main__':main()
