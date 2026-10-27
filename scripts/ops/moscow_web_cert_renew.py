import ipaddress,socket,subprocess
from pathlib import Path
public_ip_file = Path('/etc/arcvpn-web-tls/public-ip')
public_ip = str(ipaddress.IPv4Address(public_ip_file.read_text().strip())) if public_ip_file.exists() else '85.198.101.79'
if public_ip in {item[4][0] for item in socket.getaddrinfo('arccnet.space',80,socket.AF_INET)}:
    subprocess.run(['certbot','certonly','--webroot','-w','/var/www/arc-guide-acme',
        '--cert-name','arccnet.space','-d','arccnet.space','--keep-until-expiring',
        '--non-interactive','--agree-tos','--register-unsafely-without-email',
        '--deploy-hook','/usr/local/lib/arcvpn-web-cert-sync.sh'],check=True)
