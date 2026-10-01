"""Export only the owner's current FI CDN URI to a private local file."""
import os
import json
from pathlib import Path
from scripts.ops.enroll_node_telemetry import connect

REMOTE="""cd /root/ArcVPN && venv/bin/python - <<'PY'
import json,urllib.parse
import subscription_api as a
from database.connection import get_db
with get_db() as c:
 r=c.execute("SELECT k.sub_id FROM vpn_keys k JOIN users u ON u.id=k.user_id WHERE lower(u.username)='progressive_dev' AND k.expires_at>datetime('now') ORDER BY k.expires_at DESC LIMIT 1").fetchone()
key=a.get_active_key_by_subscription_id(r['sub_id'])
links=a.ASYNC_EXECUTOR.run(a._native_remnawave_links(key),timeout=20)
link=next(v for v in links if urllib.parse.urlsplit(v).hostname=='cdn-de.arccnet.space' and urllib.parse.parse_qs(urllib.parse.urlsplit(v).query).get('path')==['/api-fin'])
link=a._normalize_native_share_link(link).rsplit('#',1)[0]+'#'+urllib.parse.quote('ArcVPN CDN direct Finland test')
print(json.dumps({'link':link}))
PY"""

def main():
    target=Path(os.environ['ARCVPN_PRIVATE_TEST_FILE'])
    with connect('217.60.33.38',os.environ.pop('ARCVPN_CONTROL_PASSWORD'),'SHA256:5/opvVBUsfq8T2bit1TTuG4i5eCBWrli//df/OPDebs') as c:
        _,out,err=c.exec_command(REMOTE,timeout=40)
        data=out.read();err.read()
        if out.channel.recv_exit_status():
            raise RuntimeError('Private link export failed; output withheld')
        value=json.loads(data)['link']
    if not value.startswith('vless://'):
        raise RuntimeError('Unexpected link format')
    target.write_text(value+'\n',encoding='utf-8')
    print('Owner Finland CDN link exported; credentials withheld')

if __name__=='__main__':main()
