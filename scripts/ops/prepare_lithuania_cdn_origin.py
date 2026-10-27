"""Prepare Lithuania for existing CDN URLs before switching the origin."""
import shutil
import subprocess
from pathlib import Path

config = Path('/etc/nginx/sites-available/arcvpn-lt')
backup = Path('/root/arcvpn-lt-before-20261027/nginx-before-global.conf')
original = config.read_text()
if not backup.exists():
    shutil.copy2(config, backup)
if '# ArcVPN existing CDN clients' in original:
    raise SystemExit('Already prepared; inspect current configuration')

locations = '\n    # ArcVPN existing CDN clients\n'
for old, new, port in [
    ('/api-se-test-4096', '/api-lt-test-4096', 10012),
    ('/api-se-test-24000', '/api-lt-test-24000', 10013),
    ('/api-se-65536', '/api-lt-65536', 10014),
    ('/api-se-32768', '/api-lt-32768', 10015),
    ('/api-test', '/api-lt-test', 10001),
    ('/api-ee-direct', '/api-lt-direct', 10002),
    ('/api-ee-reserve', '/api-lt-reserve', 10003),
]:
    locations += f'''    location ^~ {old} {{
        rewrite ^{old}(.*)$ {new}$1 break;
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1; proxy_set_header Host cdn-de.arccnet.space;
        proxy_set_header Connection ""; proxy_buffering off; proxy_request_buffering off;
        proxy_cache off; proxy_read_timeout 3600s; proxy_send_timeout 3600s;
        client_max_body_size 0; add_header Cache-Control "no-store, no-transform" always;
        access_log off;
    }}\n'''

for path in ('/sub/', '/import/', '/api/device/import/'):
    locations += f'''    location ^~ {path} {{
        proxy_pass https://217.60.33.38;
        proxy_http_version 1.1; proxy_ssl_server_name on; proxy_ssl_name sub.arccnet.space;
        proxy_ssl_verify on; proxy_ssl_verify_depth 3;
        proxy_ssl_trusted_certificate /etc/ssl/certs/ca-certificates.crt;
        proxy_set_header Host sub.arccnet.space; proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Connection ""; proxy_buffering off; proxy_request_buffering off;
        proxy_cache off; proxy_no_cache 1; proxy_cache_bypass 1;
        proxy_hide_header Cache-Control; add_header Cache-Control "private, no-store, no-cache, must-revalidate" always;
        proxy_read_timeout 60s; proxy_send_timeout 60s; access_log off;
    }}\n'''

locations += '''    location ~ "^/[A-Za-z0-9_-]{20,128}$" {
        proxy_pass https://217.60.33.38;
        proxy_http_version 1.1; proxy_ssl_server_name on; proxy_ssl_name sub.arccnet.space;
        proxy_ssl_verify on; proxy_ssl_verify_depth 3;
        proxy_ssl_trusted_certificate /etc/ssl/certs/ca-certificates.crt;
        proxy_set_header Host sub.arccnet.space; proxy_set_header X-Forwarded-Proto https;
        proxy_buffering off; proxy_cache off; proxy_no_cache 1; proxy_cache_bypass 1;
        proxy_hide_header Cache-Control; add_header Cache-Control "private, no-store, no-cache, must-revalidate" always;
        access_log off;
    }\n'''

try:
    target = ' location / { return 404; }'
    assert target in original
    config.write_text(original.replace(target, locations + target, 1))
    subprocess.run(['nginx', '-t'], check=True)
    subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
except Exception:
    config.write_text(original)
    raise
print('Lithuania CDN origin prepared: old and LT paths, verified-TLS subscription proxy')
