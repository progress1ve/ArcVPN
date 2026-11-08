"""Deploy only the reviewed node HTML; keep nginx/VPN configuration untouched.

Use ARC_SITE_PASSWORD privately for LT/SE. NL uses the existing operations key.
Known-host verification is mandatory. Run without --apply for a read-only audit.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex

import paramiko


TARGETS = {
    'nl-royale': ('45.141.202.248', '/var/www/arcvpn-royale-site', 'nl.arccnet.space'),
    'lt-cherry': ('88.216.62.135', '/var/www/arcvpn-lt-site', 'lt.arccnet.space'),
    'se-hostup': ('136.148.220.228', '/var/www/arcvpn-se-site', 'se.arccnet.space'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('alias', choices=TARGETS)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    host, root, domain = TARGETS[args.alias]
    source = Path(__file__).resolve().parents[2] / 'deploy/node-site/index.html'
    payload = source.read_bytes()
    assert b'Arccnet Tools' in payload and b'canvas.toBlob' in payload
    digest = hashlib.sha256(payload).hexdigest()
    client = paramiko.SSHClient()
    client.load_system_host_keys(str(Path.home() / '.ssh/known_hosts'))
    auth = {'key_filename': str(Path.home() / '.ssh/id_ed25519_arcvpn_nl_ops')} if args.alias == 'nl-royale' else {'password': os.environ.pop('ARC_SITE_PASSWORD')}
    client.connect(host, username='root', allow_agent=False, look_for_keys=False, timeout=10, **auth)
    candidate = root + '/.index-arccnet-tools-' + digest[:12] + '.new'
    try:
        if args.apply:
            with client.open_sftp() as sftp:
                with sftp.file(candidate, 'wb') as stream:
                    stream.write(payload)
                sftp.chmod(candidate, 0o644)
        remote = r'''
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
root=Path(ROOT);target=root/'index.html';candidate=Path(CANDIDATE)
assert root.is_dir() and target.is_file()
def configuration():
 p=subprocess.run(['nginx','-T'],capture_output=True,check=True)
 return hashlib.sha256(p.stdout).hexdigest()
before=configuration()
result={'domain':DOMAIN,'config_before':before,'old_html':hashlib.sha256(target.read_bytes()).hexdigest()}
if APPLY:
 assert candidate.parent==root and hashlib.sha256(candidate.read_bytes()).hexdigest()==DIGEST
 backup=Path('/root/arcvpn-site-backups')/time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())
 backup.mkdir(parents=True,exist_ok=False,mode=0o700)
 shutil.copy2(target,backup/'index.html');os.chmod(backup/'index.html',0o600)
 (backup/'manifest.json').write_text(json.dumps(result,indent=2));os.chmod(backup/'manifest.json',0o600)
 os.replace(candidate,target)
 result.update(backup=str(backup),new_html=hashlib.sha256(target.read_bytes()).hexdigest())
result['config_after']=configuration()
assert result['config_after']==before,'Unexpected configuration change'
print(json.dumps(result))
'''
        for key, value in {'ROOT': root, 'CANDIDATE': candidate, 'DOMAIN': domain, 'APPLY': args.apply, 'DIGEST': digest}.items():
            remote = remote.replace(key, repr(value))
        _, stdout, _ = client.exec_command('python3 -c ' + shlex.quote(remote), timeout=25)
        output = stdout.read().decode()
        if stdout.channel.recv_exit_status() != 0:
            raise RuntimeError('Node website deployment failed; inspect target privately before retrying')
        print(json.dumps({'alias': args.alias, **json.loads(output)}))
    finally:
        client.close()


if __name__ == '__main__':
    main()
