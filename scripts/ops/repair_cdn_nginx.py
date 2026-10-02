"""Run on Estonia: scoped, reversible CDN origin header/connection repair."""
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    site = Path('/etc/nginx/sites-enabled/arcvpn-xhttp').resolve()
    config = Path('/etc/nginx/nginx.conf')
    old_site, old_config = site.read_text(), config.read_text()
    assert 'large_client_header_buffers 8 8k;' in old_site
    assert 'worker_connections 768;' in old_config
    upstreams = ''.join(
        f'upstream arc_cdn_{port} {{\n    server 127.0.0.1:{port};\n'
        '    keepalive 32;\n    keepalive_requests 10000;\n'
        '    keepalive_timeout 60s;\n}\n'
        for port in (10002, 10003)
    )
    new_site = upstreams + old_site.replace(
        'large_client_header_buffers 8 8k;', 'large_client_header_buffers 4 64k;'
    )
    for port in (10002, 10003):
        new_site = new_site.replace(f'proxy_pass http://127.0.0.1:{port};',
                                    f'proxy_pass http://arc_cdn_{port};')
    backup = Path(tempfile.mkdtemp(prefix='arcvpn-nginx-upload-before.', dir='/root'))
    shutil.copy2(site, backup / 'arcvpn-xhttp')
    shutil.copy2(config, backup / 'nginx.conf')
    try:
        site.write_text(new_site)
        config.write_text(old_config.replace('worker_connections 768;', 'worker_connections 4096;'))
        subprocess.run(['nginx', '-t'], check=True)
        subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
    except Exception:
        site.write_text(old_site)
        config.write_text(old_config)
        subprocess.run(['nginx', '-t'], check=True)
        raise
    print('backup=' + str(backup))


if __name__ == '__main__':
    main()
