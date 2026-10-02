"""Preserve existing subscription and import URL shapes at the shared CDN origin."""

from pathlib import Path
import shutil
import subprocess
import tempfile


CONFIG = Path('/etc/nginx/sites-enabled/arcvpn-xhttp')
BASE = '    location ^~ /sub/ {\n'
EXTRA = (
    '    location ^~ /import/ {\n',
    '    location ^~ /api/device/import/ {\n',
    '    location ~ "^/[A-Za-z0-9_-]{20,128}$" {\n',
)


def main():
    path = CONFIG.resolve()
    old = path.read_text()
    assert old.count(BASE) == 1
    if all(item in old for item in EXTRA):
        print('Subscription URL routes already present')
        return
    assert not any(item in old for item in EXTRA), 'Partial route change: inspect manually'

    start = old.index(BASE)
    end = old.index('    }\n', start) + len('    }\n')
    block = old[start:end]
    assert 'proxy_pass https://217.60.33.38;' in block
    assert 'proxy_ssl_verify on;' in block
    assert 'proxy_set_header Host sub.arccnet.space;' in block
    assert 'proxy_cache off;' in block

    additional = ''.join(block.replace(BASE, location, 1) for location in EXTRA)
    backup = Path(tempfile.mkdtemp(prefix='arcvpn-sub-cdn-routes-before.', dir='/root'))
    shutil.copy2(path, backup / path.name)
    try:
        path.write_text(old[:end] + additional + old[end:])
        subprocess.run(['nginx', '-t'], check=True)
        subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
    except Exception:
        path.write_text(old)
        subprocess.run(['nginx', '-t'], check=True)
        raise
    print('backup=' + str(backup))


if __name__ == '__main__':
    main()
