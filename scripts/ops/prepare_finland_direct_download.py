"""Owner-authorized TLS endpoint for a private split-XHTTP experiment."""
import io
import os
from scripts.ops.enroll_node_telemetry import connect, run

CONFIG = b'''server {
    listen 8444 ssl;
    server_name fin.arccnet.space;
    ssl_certificate /etc/letsencrypt/live/fin.arccnet.space/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fin.arccnet.space/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    access_log off;
    location /api-fin {
        proxy_pass http://127.0.0.1:10001;
        proxy_http_version 1.1;
        proxy_set_header Host cdn-de.arccnet.space;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        client_max_body_size 0;
        add_header Cache-Control "no-store, no-transform" always;
        add_header X-Accel-Buffering no always;
    }
    location / { return 404; }
}
'''
TARGET = '/etc/nginx/conf.d/arcvpn-direct-download.conf'

def main():
    with connect('151.241.137.174', os.environ.pop('ARCVPN_NODE_PASSWORD'),
                 'SHA256:17lgGdIAIQpP/iCQqeF27YDVetkA7nC8Z2VAh+gDbD4') as client:
        with client.open_sftp() as sftp:
            try:
                with sftp.open(TARGET, 'rb') as current:
                    if current.read() != CONFIG:
                        raise RuntimeError('Existing dedicated config differs; preserve it')
                print('Dedicated config already matches')
                return
            except FileNotFoundError:
                pass
            run(client, "test -z \"$(ss -lntH 'sport = :8444')\"")
            backup = run(client, 'mktemp -d /root/arcvpn-direct-download-before.XXXXXX').decode().strip()
            run(client, f'cp -a /etc/nginx {backup}/nginx')
            sftp.putfo(io.BytesIO(CONFIG), TARGET)
            sftp.chmod(TARGET, 0o644)
            try:
                run(client, 'nginx -t && systemctl reload nginx && systemctl is-active nginx')
            except Exception:
                sftp.remove(TARGET)
                run(client, 'nginx -t && systemctl reload nginx')
                raise
            print('TLS endpoint installed; syntax/reload passed. Backup: ' + backup)
            print(run(client, "ss -lntH 'sport = :8444'").decode().strip())

if __name__ == '__main__':
    main()
