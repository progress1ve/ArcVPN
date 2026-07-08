import sys, io, paramiko
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
cmd = """
cd /root/ArcVPN && python3 << 'PYEOF'
import asyncio, uuid, json
from bot.services.panels.xui import XUIClient

async def test():
    server = {"host": "2.26.84.210", "port": 2082, "protocol": "https", "web_base_path": "/hCcSxQCgxt570Hcu3D/", "login": "hUGKQISiDW", "password": "2aDnyGFo9y", "name": "t"}
    c = XUIClient(server)
    await c.login()
    
    # Try with client wrapper (maybe API changed in 3.3.1)
    client = {"email": "test_cw_" + uuid.uuid4().hex[:4]}
    payload = {"client": client, "inboundIds": [1]}
    
    try:
        result = await c._request("POST", "/panel/api/clients/add", data=payload, json_body=True)
        print("wrapped:", result.get("success"), result.get("msg","")[:60])
    except Exception as e:
        print("wrapped:", str(e)[:60])
    
    await c.close()

asyncio.run(test())
PYEOF
"""
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('2.26.84.210', username='root', password='P9TyuQwEvedOBpC9hI9z', timeout=30, look_for_keys=False, allow_agent=False)
stdin, stdout, stderr = c.exec_command(cmd, timeout=30)
out = stdout.read().decode('utf-8', 'replace')
err = stderr.read().decode('utf-8', 'replace')
c.close()
sys.stdout.write(out)
if err.strip():
    sys.stdout.write('\nSTDERR: ' + err.strip() + '\n')
