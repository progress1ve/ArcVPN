import sys, io, paramiko

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

cmd = """
echo '=== trial_enabled setting ==='
sqlite3 /root/ArcVPN/database/vpn_bot.db "SELECT * FROM settings WHERE key='trial_enabled';"
echo ''
echo '=== is_trial_enabled code ==='
grep 'trial_enabled' /root/ArcVPN/database/db_settings.py | head -3
echo ''
echo '=== bot service status ==='
systemctl status arcvpn-bot.service --no-pager -n 3
echo ''
echo '=== subscription service status ==='
systemctl status arcvpn-subscription.service --no-pager -n 3
"""

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('2.26.84.210', username='root', password='P9TyuQwEvedOBpC9hI9z', timeout=30, look_for_keys=False, allow_agent=False)
stdin, stdout, stderr = c.exec_command(cmd, timeout=60)
out = stdout.read().decode('utf-8', 'replace')
err = stderr.read().decode('utf-8', 'replace')
c.close()
sys.stdout.write(out)
if err.strip():
    sys.stdout.write('\nSTDERR: ' + err.strip() + '\n')
