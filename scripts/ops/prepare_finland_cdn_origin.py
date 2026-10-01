"""Owner-approved shared CDN origin: FI local path, EE relay without Moscow."""
import os
import re
from scripts.ops.enroll_node_telemetry import connect, run, put_private

TARGET='/etc/nginx/conf.d/arcvpn-finland.conf'
BLOCK='''    # ArcVPN shared CDN origin: preserve Estonia exit without Moscow.
    location /api-test {
        proxy_pass http://87.251.19.197:80;
        proxy_http_version 1.1;
        proxy_set_header Host cdn-de.arccnet.space;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        client_max_body_size 0;
    }
'''

def prepare(source):
    source=source.replace('\r\n','\n').replace('\r','')
    if 'location /api-fin' not in source or 'server_name fin.arccnet.space cdn-de.arccnet.space;' not in source:
        # Idempotent subsequent run accepts the origin Host alias too.
        if 'server_name fin.arccnet.space cdn-de.arccnet.space origin.arccnet.space;' not in source:
            raise ValueError('unexpected_origin_config')
    if 'location /api-test' in source:
        if 'proxy_pass http://87.251.19.197:80;' not in source:
            raise ValueError('unknown_existing_estonia_route')
        return source
    source=source.replace('server_name fin.arccnet.space cdn-de.arccnet.space;',
                          'server_name fin.arccnet.space cdn-de.arccnet.space origin.arccnet.space;')
    return re.sub(r'(?m)^(\s*)location /api-fin',BLOCK+r'\1location /api-fin',source,count=1)

def main():
    password=os.environ.pop('ARCVPN_NODE_PASSWORD')
    with connect('151.241.137.174',password,'SHA256:17lgGdIAIQpP/iCQqeF27YDVetkA7nC8Z2VAh+gDbD4') as c:
        sftp=c.open_sftp()
        with sftp.open(TARGET,'rb') as stream: original=stream.read()
        desired=prepare(original.decode()).encode()
        if desired==original:
            print('Origin already prepared');return
        backup=run(c,"mktemp /root/arcvpn-fi-cdn-before.XXXXXX").decode().strip()
        put_private(sftp,original,backup,0o600)
        try:
            put_private(sftp,desired,TARGET,0o644)
            run(c,'nginx -t && systemctl reload nginx && systemctl is-active nginx')
        except Exception:
            put_private(sftp,original,TARGET,0o644)
            run(c,'nginx -t && systemctl reload nginx')
            raise
        print('Finland origin prepared; nginx active; backup:',backup)
        sftp.close()

if __name__=='__main__':main()
