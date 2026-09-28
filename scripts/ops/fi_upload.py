"""Upload one non-secret source through pinned SSH and validate nginx."""
import os
import sys
from pathlib import Path
import paramiko
sys.stdout.reconfigure(encoding='utf-8')
client = paramiko.SSHClient()
client.load_host_keys(str(Path.home() / '.ssh' / 'known_hosts'))
client.set_missing_host_key_policy(paramiko.RejectPolicy())
client.connect('92.42.102.139', username='root', password=os.environ.pop('ARCVPN_SSH_PASSWORD'),
               allow_agent=False, look_for_keys=False, timeout=20)
try:
    with client.open_sftp() as sftp:
        sftp.put(str(Path(__file__).resolve().parents[2] / 'deploy/nginx/finland-node.conf'),
                 '/etc/nginx/conf.d/arcvpn-finland.conf')
        sftp.put(str(Path(__file__).resolve().parents[2] / 'deploy/systemd/arcvpn-fi-port-guard.service'),
                 '/etc/systemd/system/arcvpn-fi-port-guard.service')
    _, out, err = client.exec_command('nginx -t && systemctl reload nginx && systemctl daemon-reload && systemctl enable --now arcvpn-fi-port-guard.service && ss -lnt | grep -E "443|10001|22600"', timeout=20)
    print(out.read().decode())
    print(err.read().decode())
    if out.channel.recv_exit_status(): raise RuntimeError('Validation failed')
finally: client.close()
