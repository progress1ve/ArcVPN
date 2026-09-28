"""Pinned SSH bootstrap. Credentials from process environment; no secret logging."""
import json
import os
from pathlib import Path
import paramiko

def connect(host, variable):
    client = paramiko.SSHClient()
    client.load_host_keys(str(Path.home() / '.ssh' / 'known_hosts'))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(host, username='root', password=os.environ.pop(variable),
                   allow_agent=False, look_for_keys=False, timeout=20)
    return client

def execute(client, command, input_data=None):
    stdin, stdout, stderr = client.exec_command(command, timeout=60)
    if input_data is not None:
        stdin.write(input_data)
        stdin.flush()
        stdin.channel.shutdown_write()
    output = stdout.read()
    error = stderr.read()
    if stdout.channel.recv_exit_status():
        raise RuntimeError('Remote operation failed; inspect bounded server diagnostics')
    return output

fi = connect('92.42.102.139', 'ARCVPN_FI_PASSWORD')
pl = connect('217.60.33.38', 'ARCVPN_PL_PASSWORD')
try:
    code = """import os,json,base64,secrets
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PrivateFormat,PublicFormat,NoEncryption
p=Path('/root/arcvpn-fi-reality.json')
if not p.exists():
 k=X25519PrivateKey.generate()
 enc=lambda b:base64.urlsafe_b64encode(b).decode().rstrip('=')
 data={'private_key':enc(k.private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption())), 'public_key':enc(k.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)), 'short_id':secrets.token_hex(8)}
 fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w') as f:json.dump(data,f)
print(p.read_text())
"""
    material = execute(fi, 'python3 -', code)
    result = execute(pl, 'cd /root/ArcVPN && venv/bin/python /opt/arcvpn/staging/provision_finland_node.py', material.decode())
    print(result.decode().strip())
    with pl.open_sftp() as source:
        secret = source.open('/root/ArcVPN/.secrets/finland-node-secret.txt').read().decode().strip()
    compose = f'''services:
  remnanode:
    image: remnawave/node:3.4.1
    container_name: remnanode
    hostname: remnanode
    restart: always
    network_mode: host
    environment:
      NODE_PORT: 22600
      SECRET_KEY: {json.dumps(secret)}
    logging:
      driver: json-file
      options:
        max-size: 10m
        max-file: '3'
'''
    execute(fi, 'install -d -m 700 /opt/remnanode')
    with fi.open_sftp() as dest:
        with dest.open('/opt/remnanode/docker-compose.yml', 'w') as output: output.write(compose)
        dest.chmod('/opt/remnanode/docker-compose.yml', 0o600)
    del material, secret, compose
    print(execute(fi, 'cd /opt/remnanode && docker compose up -d >/dev/null 2>&1 && docker inspect remnanode --format "{{.State.Status}}"').decode().strip())
finally:
    fi.close()
    pl.close()
