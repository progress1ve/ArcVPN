# LTE, XHTTP, CDN, DNS, and certificates

Use this only for anti-block/CDN paths.

- LTE/CDN/XHTTP is a separate product path with traffic multiplier 1; normal profiles also remain multiplier 1. Separate quota and identity are product concerns, not a billing multiplier.
- Known working DHost baseline: XHTTP `packet-up`, `/api-test`, upstream `OPTIONS`, compatible padding, and origin conversion `OPTIONS -> POST` when required.
- Happ fingerprint baseline is `firefox`, with `edge` fallback; `chrome` is known to fail on affected routes.
- Keep CDN hosts hidden from ordinary auto-selection unless the documented fallback design explicitly requires them.
- Before issuing a certificate, verify DNS ownership/records and distinguish the origin hostname from the CDN hostname.
- Validate both CDN edge and origin independently: DNS, TLS/SNI, HTTP method behavior, origin reachability, Xray logs, and real tunneled traffic during throttling.
- Do not create a new CDN resource merely for display. Create one only when isolation, origin policy, billing, certificate, or failure-domain requirements justify it.
- Rollback removes the host from subscription delivery first, then reverts CDN/origin configuration; it never rotates user UUIDs.

Before changing DNS, CDN, an origin group, or subscription rendering, record and obtain acceptance for this topology table:

| Visible profile | Client hostname | CDN resource | Origin group | Active / backup | Host and SNI | Inbound and path | Multiplier | Public URL impact | Failure behavior | Rollback |
|---|---|---|---|---|---|---|---|---|---|---|

Do not infer missing cells from naming (for example, a historic country code in a hostname). Verify provider state and runtime state independently.
