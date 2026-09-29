"""Strict pinned SSH; target-generated key and node secret stay in memory."""
import json
import os
from pathlib import Path
import paramiko


def connect(host, var):
    c = paramiko.SSHClient()
    c.load_host_keys(str(Path.home() / '.ssh/known_hosts'))
    c.set_missing_host_key_policy(paramiko.RejectPolicy())
    c.connect(host, username='root', password=os.environ.pop(var), allow_agent=False, look_for_keys=False, timeout=15)
    return c


def execute(c, command, data=None):
    stdin, stdout, stderr = c.exec_command(command, timeout=45)
    if data:
        stdin.write(data)
        stdin.flush()
        stdin.channel.shutdown_write()
    result = stdout.read()
    stderr.read()
    if stdout.channel.recv_exit_status():
        raise RuntimeError('Remote operation failed; inspect bounded diagnostics')
    return result


fi = connect('151.241.137.174', 'ARCVPN_FI_PASSWORD')
pl = connect('217.60.33.38', 'ARCVPN_PL_PASSWORD')
try:
    code = '''import os,json,base64,secrets
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PrivateFormat,PublicFormat,NoEncryption
p=Path('/root/arcvpn-fi-reality.json')
if not p.exists():
 k=X25519PrivateKey.generate();enc=lambda b:base64.urlsafe_b64encode(b).decode().rstrip('=')
 d={'private_key':enc(k.private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption())), 'public_key':enc(k.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)), 'short_id':secrets.token_hex(8)}
 with os.fdopen(os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:json.dump(d,f)
print(p.read_text())
'''
    material = execute(fi, 'python3 -', code)
    print(execute(pl, 'cd /root/ArcVPN && venv/bin/python /opt/arcvpn/staging/replace_finland_node.py', material.decode()).decode().strip())
    with pl.open_sftp() as s:
        secret = s.open('/root/ArcVPN/.secrets/finland-node-secret.txt').read().decode().strip()
    execute(fi, 'install -d -m 700 /opt/remnanode')
    with fi.open_sftp() as s:
        with s.open('/opt/remnanode/node.env', 'w') as f:
            f.write('NODE_PORT=22600\nSECRET_KEY=' + secret + '\n')
        s.chmod('/opt/remnanode/node.env', 0o600)
        for local, remote in [('deploy/systemd/arcvpn-fi-port-guard.service', '/etc/systemd/system/arcvpn-fi-port-guard.service')]:
            s.put(local, remote)
    del secret, material
    print(execute(fi, 'systemctl daemon-reload && systemctl enable --now arcvpn-fi-port-guard && systemd-run --unit=arcvpn-fi-node-start --no-block /bin/bash -c "docker pull remnawave/node:3.4.1 && docker run -d --name remnanode --hostname remnanode --network host --restart always --env-file /opt/remnanode/node.env --log-opt max-size=10m --log-opt max-file=3 remnawave/node:3.4.1"').decode().strip())
finally:
    fi.close()
    pl.close()
