"""Expose existing ACME webroot on the subscription HTTPS origin for CDN renewal."""
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    path = Path('/etc/nginx/sites-enabled/arcvpn-control-plane').resolve()
    old = path.read_text()
    marker = '    server_name sub.arccnet.space;\n'
    assert old.count(marker) == 1
    location = ('    location ^~ /.well-known/acme-challenge/ {\n'
                '        root /var/www/html;\n        try_files $uri =404;\n    }\n')
    first_server = old.split('server {', 2)[1]
    if '/.well-known/acme-challenge/' in first_server:
        print('HTTPS ACME origin already prepared')
        return
    backup = Path(tempfile.mkdtemp(prefix='arcvpn-sub-cdn-origin-before.', dir='/root'))
    shutil.copy2(path, backup / 'arcvpn-control-plane')
    try:
        path.write_text(old.replace(marker, marker + location, 1))
        subprocess.run(['nginx', '-t'], check=True)
        subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
    except Exception:
        path.write_text(old)
        subprocess.run(['nginx', '-t'], check=True)
        raise
    print('backup=' + str(backup))


if __name__ == '__main__':
    main()
