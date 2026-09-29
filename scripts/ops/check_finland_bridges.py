"""Transfer restricted canaries in memory and test both directions."""
import os
from pathlib import Path
import paramiko

def connect(host, variable):
    c = paramiko.SSHClient()
    c.load_host_keys(str(Path.home() / '.ssh/known_hosts'))
    c.connect(host, username='root', password=os.environ.pop(variable),
              look_for_keys=False, allow_agent=False, timeout=12)
    return c

pl = connect('217.60.33.38', 'ARCVPN_PL_PASSWORD')
fi = connect('151.241.137.174', 'ARCVPN_FI_PASSWORD')
try:
    for target, name, binary, label in [
        (fi, 'fi-to-ru-canary.json', '/opt/arcvpn-canary-xray', 'FI -> Moscow')]:
        with pl.open_sftp() as source, target.open_sftp() as destination:
            with source.open('/opt/arcvpn/staging/' + name) as f:
                data = f.read()
            remote = '/root/' + name
            with destination.open(remote, 'wb') as f:
                f.write(data)
            destination.chmod(remote, 0o600)
        _, copied, errors = target.exec_command(
            'docker cp remnanode:/usr/local/bin/xray ' + binary + '; chmod 700 ' + binary)
        copied.read()
        errors.read()
        command = (f'{binary} run -c {remote} >/dev/null 2>&1 & canaryPid=$!; '
                   'sleep 2; curl --socks5-hostname 127.0.0.1:18084 --max-time 12 '
                   '-s -w " http=%{http_code}" https://api.ipify.org; kill "$canaryPid"')
        _, stdout, stderr = target.exec_command(command, timeout=25)
        result = stdout.read().decode()
        stderr.read()
        print(label + ': ' + result)
finally:
    pl.close()
    fi.close()
