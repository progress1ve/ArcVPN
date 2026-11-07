# Auto production decision — 2026-11-07

Owner authorized independent study, selection/deployment and removal of the
owner-only LTE Auto trial. Preserve direct NL first, CDN strictly on observed
NL failure; preserve identities, quotas, URLs and no-LTE exclusion.

## Source review

Checked Xray26.7.28 (remote diagnostic core) and26.10.21 (previously identified
owner client version). Their relevant implementations agree:

- leastPing uses availability and measured probe delay, not file throughput.
- leastLoad uses observations including delay/deviation and failed-probe fraction,
  qualifies candidates and randomly chooses from its selected group. It does not
  measure VPSCPU or bandwidth. expected2 is not bonding of two paths.
- Burst probes are scheduled in interval*sampling windows, randomly within the
  window. Results update as individual requests finish; no fixed15s failover.
- Probe connections disable HTTP keepalive. GET consumes the response body;
  default HEAD does not. Our probe returns204, so explicitGET is consistency with
  Best Bypass, not proof of long-file health. Status codes alone are not validated
  by this implementation as an application-specific success contract.

Sources:
https://github.com/XTLS/Xray-core/blob/v26.10.21/app/router/strategy_leastload.go
https://github.com/XTLS/Xray-core/blob/v26.10.21/app/observatory/burst/healthping.go
https://github.com/XTLS/Xray-core/blob/v26.10.21/app/observatory/burst/ping.go

## Remote checks

All tests originated from Moscow VPS, not owner's PC or mobile network. Same
published owner configurations, same core and loopback TCP relay to Royale.
Closing relay and existing relay sockets simulated total NL failure. Restoring
relay tested recovery. No server/node routing/firewall changes. Download bodies
discarded and exact1048576-byte HTTP200 completion required. Attempts alternate
short HTTPS204 and file transfers within each phase; cases ran sequentially,
so this is a limited diagnostic, not randomized proof of speed superiority.

| Case | Normal/failure/recovery routing | Extra HTTPS204 | Complete1MiB files |
|---|---|---:|---:|
| Current HEAD + leastPing | Passed all3phases |2/2|1/2|
| Trial GET + leastLoad | Passed all3phases |1/2|0/2|
| GET + leastPing control | Passed all3phases |2/2|3/6|

Important measurement correction: the comparison harness's failed-phase seconds
include follow-up transfers before recording the phase result. They must NOT be
interpreted as isolated failover latency or used to rank switching speed. An
intermediate commentary ranking leastLoad switching as slower was premature;
this report and the evidence metadata correct it. File success/failure outcomes
are independent of that timing error. Previous standalone trial41.4s/12.18s
gate did not include follow-up transfers and remains a separate valid sample.

Raw sanitized comparison:
`evidence/auto-production-review-20261107.json`.

## Decision

Promote only explicitGET to shared LTE Auto; retain leastPing,15s/2/5s, four
existing CDN candidates and finalcdn-safe, without broadening CDN entitlement.
Remove the trial hook and disable its private state. No-LTE Auto and every other
profile remain unchanged. This is a conservative selected version, not a claim
that GET is faster or that all intermittent CDN failures are fixed.

Reasons: leastLoad has no positive controlled file-completion evidence in this
batch; its stricter eligibility may often fall through to the same unfiltered
cdn-safe when no candidate qualifies. Do not promote a more complex mechanism
solely from its name or a small subjective sample. Existing probes do not certify
native Telegram media, selective app restrictions, or wake-from-screen-off.

Do not copy Midas2m interval wholesale: fewer probes may reduce traffic but
increase failure-detection time. Do not add duplicate candidates on the same
origin as if they were independent capacity. Do not tune phone keepalive from
one30s screen-off /10s reconnect observation without a reproduced mechanism.

Remaining issue: CDN HTTPS/file delivery still intermittently fails in all tested
variants; origin/edge transport diagnosis is a separate next stage. Shared Auto
retains working direct NL whenever observed available. Forced local failure is
not reproduction of a particular mobile operator's restrictions.

## Deployment acceptance

Published cde89080, Poland fast-forward pulled, only subscription service
restarted.28 focused tests passed. Fresh public JSON owner20/LTE18/noLTE10
matched protected snapshots except explicitGET in LTE Auto and removal of owner
trial; all plain/base64 lists unchanged. Trial hook removed and private state
disabled. No-LTE remains NL-only with30s/3/5s and no XHTTP entitlement.

Separate final gate used the actual published Auto without follow-up downloads
inside its timing: normal NL204; blocked NL relay→successfulCDN204 at21.0s;
restored relay→NL204 at36.82s. One randomized-probe sample is not a failover SLA
or a speed ranking. Evidence: `evidence/auto-production-final-gate-20261107.json`.
All transient client inputs/processes removed, Moscow nginx and control-plane
bot/API healthy. Existing ordinary nodes were not restarted.
