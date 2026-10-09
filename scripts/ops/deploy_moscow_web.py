"""Deploy committed frontend to Moscow; TLS material travels only in SSH memory."""
import os,re,sys,json
from pathlib import Path
from enroll_node_telemetry import connect,run,put_private
def main():
 with connect('217.60.33.38',os.environ.pop('ARC_PL_PASS'),'SHA256:5/opvVBUsfq8T2bit1TTuG4i5eCBWrli//df/OPDebs') as pl:
  revision=run(pl,'cd /root/ArcVPN && git rev-parse HEAD').decode().strip()
  assert re.fullmatch('[0-9a-f]{40}',revision)
  archive=run(pl,'tar -C /root/ArcVPN -czf - webapp_dist',timeout=30)
  with pl.open_sftp() as s:
   cert=s.open('/etc/letsencrypt/live/arccnet.space/fullchain.pem').read()
   key=s.open('/etc/letsencrypt/live/arccnet.space/privkey.pem').read()
   config=s.open('/root/ArcVPN/deploy/nginx/moscow-public-web.conf').read()
   helpers={remote:s.open('/root/ArcVPN/'+local).read() for local,remote in [
    ('scripts/ops/moscow_web_cert_renew.py','/usr/local/lib/arcvpn-web-cert-renew.py'),
    ('scripts/ops/moscow_web_cert_sync.sh','/usr/local/lib/arcvpn-web-cert-sync.sh'),
    ('deploy/systemd/arcvpn-web-cert.service','/etc/systemd/system/arcvpn-web-cert.service'),
    ('deploy/systemd/arcvpn-web-cert.timer','/etc/systemd/system/arcvpn-web-cert.timer')]}
 with connect('85.198.101.79',os.environ.pop('ARC_RU_PASS'),'SHA256:b6mNOJnFgDyOdYyIkP5PgyFcP0qFpUXOKKlXjCd21Go') as ru:
  release='/var/www/arcvpn-site/releases/'+revision
  run(ru,'install -d -m 700 /etc/arcvpn-web-tls && install -d -m 755 '+release+'/app')
  with ru.open_sftp() as s:
   put_private(s,cert,'/etc/arcvpn-web-tls/fullchain.pem',0o644)
   put_private(s,key,'/etc/arcvpn-web-tls/privkey.pem',0o600)
   put_private(s,archive,'/root/arcvpn-web-dist.tgz',0o600)
   put_private(s,config,'/etc/nginx/conf.d/arcvpn-public-moscow.conf',0o644)
   for dest,data in helpers.items():put_private(s,data,dest,0o700 if dest.startswith('/usr/local/lib/') else 0o644)
  run(ru,'tar -xzf /root/arcvpn-web-dist.tgz --strip-components=1 -C '+release+'/app && chmod -R a+rX '+release+' && ln -sfn '+release+' /var/www/arcvpn-site/current.new && mv -Tf /var/www/arcvpn-site/current.new /var/www/arcvpn-site/current && nginx -t && systemctl reload nginx',timeout=30)
  run(ru,'systemctl daemon-reload && systemctl enable --now arcvpn-web-cert.timer')
  print(json.dumps({'moscow_static_revision':revision,'nginx':'reloaded','private_keys_logged':False}))
if __name__=='__main__':main()
