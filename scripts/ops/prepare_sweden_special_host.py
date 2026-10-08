#!/usr/bin/env python3
"""Prepare Sweden's local WARP proxy and node certificate mount."""
import os,subprocess
from pathlib import Path


def run(command):
    subprocess.run(command,check=True,stdout=subprocess.DEVNULL)


def main():
    assert os.geteuid()==0
    if subprocess.run(['warp-cli','--accept-tos','registration','show'],capture_output=True).returncode:
        run(['warp-cli','--accept-tos','registration','new'])
    run(['warp-cli','--accept-tos','mode','proxy'])
    run(['warp-cli','--accept-tos','proxy','port','40000'])
    run(['warp-cli','--accept-tos','connect'])
    compose=Path('/opt/remnanode/docker-compose.yml')
    text=compose.read_text()
    if '/etc/letsencrypt:/etc/letsencrypt:ro' not in text:
        assert 'volumes:' not in text, 'Review existing mounts first'
        lines=text.splitlines()
        i=next(i for i,l in enumerate(lines) if 'network_mode:' in l)
        indent=lines[i][:len(lines[i])-len(lines[i].lstrip())]
        lines[i:i]=[indent+'volumes:',indent+'  - /etc/letsencrypt:/etc/letsencrypt:ro']
        with os.fdopen(os.open('/root/arcvpn-sweden-compose-before-special.yml',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:f.write(text)
        compose.write_text('\n'.join(lines)+'\n')
    run(['docker','compose','-f',str(compose),'config','--quiet'])
    run(['docker','compose','-f',str(compose),'up','-d','--no-deps','remnanode'])
    run(['docker','exec','remnanode','test','-r','/etc/letsencrypt/live/se.arccnet.space/privkey.pem'])
    run(['ufw','allow','8444/tcp'])
    run(['ufw','allow','443/udp'])
    print('Sweden WARP proxy, certificate mount and dedicated ports prepared')

if __name__=='__main__':main()
