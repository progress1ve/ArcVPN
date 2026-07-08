import sys, io, paramiko
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
cmd = "sqlite3 /root/ArcVPN/database/vpn_bot.db 'SELECT id, name, traffic_limit_gb, duration_days, price_cents FROM tariffs;'"
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
