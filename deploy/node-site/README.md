# Arccnet Tools node website

Standalone static HTML for the existing Reality TLS targets on NL/LT/SE.
No application framework, build step, backend, external font, analytics or
third-party asset is needed. All image processing happens in the browser.

Supported input/output: PNG, JPEG, WebP; one image, 20 MiB and 24 MP maximum.
Output is static; JPEG uses a white background. Metadata and colour profile
preservation are not promised. PNG ignores the quality setting.

Run a local static server and `node scripts/qa/node-site.cjs` with Playwright
installed. `PLAYWRIGHT_MODULE`, `BROWSER_CHANNEL`, `SITE_URL` and
`SITE_EVIDENCE_DIR` optionally select the runtime, browser, target and evidence
folder. QA verifies four viewport widths, actual conversions/downloads,
transparency, JPEG background, invalid inputs, keyboard FAQ and external requests.

After checks, review/commit/push and production FF-pull, then use
`python scripts/ops/deploy_node_site.py <inventory-alias> --apply`.
Targets are explicitly limited to `nl-royale`, `lt-cherry`, `se-hostup`.
For LT/SE inject `ARC_SITE_PASSWORD` from the local encrypted vault into the
process environment only; NL uses the existing operations SSH key. Never pass
a password as a CLI argument. Omitting `--apply` audits without writing.

Deployment atomically replaces only the existing root `index.html`, saving
the old file and manifest to a dated `/root/arcvpn-site-backups/` directory on
each target. It verifies the effective nginx configuration hash is unchanged.
No daemon restart, reload, VPN/CDN configuration or identity edit is required.
Verify both public hostnames and TLS at each physical node, since DNS may point
at a different node than the physical server.

Rollback: on the exact target, copy the recorded backup `index.html` to a
temporary sibling of the live file, chmod 644, then atomically rename over
the live `index.html`. Preserve all other web files and configuration. A static
HTML rollback does not require restarting nginx or the VPN node.
