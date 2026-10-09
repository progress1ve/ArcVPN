import socket,subprocess
if '85.198.101.79' in {item[4][0] for item in socket.getaddrinfo('arccnet.space',80,socket.AF_INET)}:
    subprocess.run(['certbot','certonly','--webroot','-w','/var/www/arc-guide-acme',
        '--cert-name','arccnet.space','-d','arccnet.space','--keep-until-expiring',
        '--non-interactive','--agree-tos','--register-unsafely-without-email',
        '--deploy-hook','/usr/local/lib/arcvpn-web-cert-sync.sh'],check=True)
