# Stage: AutoSelect distribution and CDN/XHTTP stability

## Goal

- Keep AutoSelect availability-aware while distributing normal connections across
  both Germany and Estonia instead of collapsing onto one lowest-variance node.
- Reproduce and identify the reported CDN/XHTTP disconnect after roughly two
  minutes without changing the published CDN topology on assumption alone.

## Accepted public contract

| Path | Candidates | Selection | CDN fallback | Public identifiers |
| --- | --- | --- | --- | --- |
| `Автовыбор | Самый быстрый` | Germany and Estonia ordinary main outbounds | `leastLoad`, retain the two best healthy candidates and randomly choose between them | existing hidden `cdn-de.arccnet.space` fallback only when main candidates are unavailable | subscription URLs, UUIDs, visible names and order unchanged |

Expected distribution is statistical rather than a hard session quota: with both
nodes healthy, Germany should normally receive about 35–65% of a sufficiently
large sample; an unavailable or failed-probe node must be excluded.

## CDN diagnostic contract

| Visible profile | Client hostname | CDN resource | Origin group | Active / backup | Host/SNI | Inbound/path | Multiplier | Failure behavior | Rollback |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| existing CDN/XHTTP bypass | `cdn-de.arccnet.space` | existing Yandex CDN | Moscow origin | Moscow to Germany, Estonia backup | `cdn-de.arccnet.space` | XHTTP `packet-up`, `/api-test` | 1 | preserve current route while collecting timed edge/origin evidence | no topology mutation in this diagnostic stage |

## Components

- `subscription_api.py`
- focused AutoSelect tests
- read-only Remnawave, Moscow, Germany and Estonia telemetry
- `.codex/stages/current.md`, `.codex/handoff.md`, `AI_CONTEXT.md`

## Non-goals

- No subscription URL, UUID, quota, visible order, DNS, CDN resource, origin,
  inbound, Host/SNI, firewall or Reality change.
- No hard central session scheduler: AutoSelect runs independently inside each
  user's Xray client, so an exact global 50/50 split cannot be guaranteed.
- Do not change XHTTP mode until a real timed tunnel proves a compatible fix.

## Acceptance

- Generated AutoSelect has `leastLoad.expected = 2`, a non-zero failed-probe
  tolerance, both ordinary main countries, and no display aliases or CDN rows in
  the healthy main pool.
- Focused tests and production subscription inspection pass.
- Production service is active after an ff-only deployment and restart.
- Current node telemetry shows Germany and Estonia connected.
- CDN conclusion is backed by bounded edge/origin logs and, where possible, a
  timed real tunnel; any unproven remediation remains explicitly open.

## Risks and rollback

- A slower but healthy node will receive more connections than before. Health
  probes and `maxRTT` continue to eject unacceptable candidates.
- Statistical balance can be uneven in a sample as small as 12 users.
- Roll back the subscription commit and restart only
  `arcvpn-subscription.service`; no node-side rollback is required.

## Verification matrix

| Check | Status | Evidence |
| --- | --- | --- |
| Live node health | Passed | Germany and Estonia connected; normal host health clean |
| Existing live distribution | Observed | Remnawave session counters showed Estonia 9, Germany 7 during diagnosis; owner observed a more skewed 10–11 vs 1–2 window |
| CDN origin errors | Observed | 108,651 successful Moscow XHTTP requests vs 35 non-2xx in rotated/current logs; clustered 5xx aligned with an origin interruption, not a steady two-minute nginx timeout |
| AutoSelect config/tests | Passed | `leastLoad.expected=2`, `tolerance=0.2`; 30 focused tests passed with the production-compatible config module |
| Production generated subscription | Pending | |
| Timed CDN tunnel | Pending | |
