# LTE, XHTTP, CDN, DNS, and certificates

Use this only for anti-block/CDN paths.

- LTE is a separate product path with traffic multiplier 10; normal profiles remain multiplier 1.
- Known working DHost baseline: XHTTP `packet-up`, `/api-test`, upstream `OPTIONS`, compatible padding, and origin conversion `OPTIONS -> POST` when required.
- Happ fingerprint baseline is `firefox`, with `edge` fallback; `chrome` is known to fail on affected routes.
- Keep CDN hosts hidden from ordinary auto-selection unless the documented fallback design explicitly requires them.
- Before issuing a certificate, verify DNS ownership/records and distinguish the origin hostname from the CDN hostname.
- Validate both CDN edge and origin independently: DNS, TLS/SNI, HTTP method behavior, origin reachability, Xray logs, and real tunneled traffic during throttling.
- Do not create a new CDN resource merely for display. Create one only when isolation, origin policy, billing, certificate, or failure-domain requirements justify it.
- Rollback removes the host from subscription delivery first, then reverts CDN/origin configuration; it never rotates user UUIDs.
