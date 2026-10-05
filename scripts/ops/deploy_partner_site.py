"""Install only the dedicated partner virtual host on the existing Poland control plane."""
import argparse
import configparser
import subprocess
from pathlib import Path


TARGET = Path("/etc/nginx/conf.d/arcvpn-partners.conf")
CERT = Path("/etc/letsencrypt/live/partners.arccnet.space/fullchain.pem")
MARKER = "# ArcVPN managed partner cabinet\n"


def run(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(arguments[0] + " failed; inspect its local service logs")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    options = parser.parse_args()
    source = Path(__file__).resolve().parents[2] / "deploy/nginx/partners-arccnet.conf"
    if not options.apply:
        print("Target: Poland control plane; partners.arccnet.space; nginx virtual host and TLS only.")
        return
    if TARGET.parent.resolve() != Path("/etc/nginx/conf.d").resolve():
        raise RuntimeError("Unexpected nginx path")
    prior = TARGET.read_text() if TARGET.exists() else None
    if prior is not None and not prior.startswith(MARKER):
        raise RuntimeError("Existing unowned partner virtual host; refusing overwrite")
    try:
        if not CERT.exists():
            TARGET.write_text(MARKER + """server {
    listen 80;
    server_name partners.arccnet.space;
    location ^~ /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://$host$request_uri; }
}
""")
            run(["nginx", "-t"])
            run(["systemctl", "reload", "nginx"])
            # Reuse the existing control-plane account; multiple ACME accounts
            # on this host otherwise make non-interactive issuance ambiguous.
            renewal = configparser.ConfigParser()
            renewal.read("/etc/letsencrypt/renewal/sub.arccnet.space.conf")
            account = renewal.get("renewalparams", "account", fallback="")
            server = renewal.get("renewalparams", "server", fallback="")
            args = ["certbot", "certonly", "--webroot", "-w", "/var/www/html",
                    "-d", "partners.arccnet.space", "--non-interactive", "--agree-tos"]
            if account:
                args += ["--account", account]
            else:
                args += ["--register-unsafely-without-email"]
            if server:
                args += ["--server", server]
            run(args)
        TARGET.write_text(MARKER + source.read_text())
        run(["nginx", "-t"])
        run(["systemctl", "reload", "nginx"])
        print("Partner HTTPS virtual host installed; nginx configuration valid and reloaded.")
    except Exception:
        if prior is None:
            TARGET.unlink(missing_ok=True)
        else:
            TARGET.write_text(prior)
        run(["nginx", "-t"])
        run(["systemctl", "reload", "nginx"])
        raise


if __name__ == "__main__":
    main()
