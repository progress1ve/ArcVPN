import sys, io, paramiko
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HOST = "2.26.84.210"
USER = "root"
PASS = "P9TyuQwEvedOBpC9hI9z"

cmd = sys.stdin.read()

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS, timeout=20, look_for_keys=False, allow_agent=False)
stdin, stdout, stderr = c.exec_command(cmd, timeout=60)
out = stdout.read().decode("utf-8", "replace")
err = stderr.read().decode("utf-8", "replace")
sys.stdout.write(out)
if err.strip():
    sys.stdout.write("\n--- STDERR ---\n" + err)
c.close()
