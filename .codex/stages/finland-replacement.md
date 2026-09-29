# Replacement Finland151.241.137.174 — 2026-09-29

Owner authorizes replacement and original FI+EE plan. Same Remnawave FI
node/profile/hosts reused with backups; credentials DPAPI-only, never Git.

2026-09-29 owner supersedes compatibility proposal: update existing /api-test
and /api-fin for every user to GET/header/X-Session-Token. No new CDN resource
or path; preserve other parameters and UUID/quota/URL identities. Clients must
refresh subscriptions. Rollback uses restricted cdn-get-before.json plus scoped
subscription renderer revert. Require real EE/FI CDN tunnels before acceptance.

| Profile | Host/SNI | CDN/origin | Inbound/path | Priority/failure | Multiplier/IDs | Rollback |
| --- | --- | --- | --- | --- | --- | --- |
| FI ordinary | fin.arccnet.space; same SNI | none | unique Reality443 | FI+EE routine peers after checks | 1; URLs/user UUID unchanged | restore profile/node/host backups and runtime |
| AutoSelect | existing FI+EE | existing CDN last fallback | existing Reality | FI+EE peers, no Germany | 1; no new subscription URL | scoped runtime revert |
| YouTube | existing FI+EE | FI/EE -> Moscow2444 | existing reciprocal service identities | verified FI joins main pool | 1; no CDN spending | remove FI from pool |
| FI bypass | cdn-de.arccnet.space; existing client TLS SNI | same resource/ee-origin -> Moscow HTTPSorigin.arccnet.space -> new FI | GET/header /api-fin -> localhost10001 | preferred FI bypass; EE /api-test also repaired GET/header, no legacy guarantee | 1; separate LTE UUID/quota unchanged | hide FI LTE host and restore restricted backups |
| Moscow EU bridge | existing Moscow | direct new FI2443 + EE2443 | service Shadowsocks | FI+EE selector after canary | unchanged identities | EE-only selector |
| Poland/NL aliases | exact verified FI endpoint/SNI | none | FI Reality443 | display aliases, not independent countries or auto entries | 1; same credentials | previous NL->EE, no Poland |

Before mutation snapshot panel config/node/hosts on Poland0600, nginx on Moscow,
and preserve old FI for rollback. No broad firewall disable; allow new FI IP
only to Moscow2444 and protect FI22600(PL)/2443(Moscow). TLS decoy certificate
must be valid forfin.arccnet.space. Owner asked to update A record; current DNS
still old FI. Do not silently replace another DNS resource or create new CDN.

Initial evidence: Moscow -> new FI22 succeeds; FI -> Moscow443HTTP200,
TCPconnect54ms. FI -> Moscow2444 times out before scoped firewall admission.
SSH ED25519 fingerprint matched local and Moscow observations:
SHA256:17lgGdIAIQpP/iCQqeF27YDVetkA7nC8Z2VAh+gDbD4; first-use pin,
not independently verified by owner VNC. New host Ubuntu22.04,2GBRAM/20GBdisk.

Acceptance: managed authorization and bindings; real HTTP/exit through Reality,
full CDN HEADER and reciprocal bridges; FI+EE generated mains with no duplicate
aliases; public/service health; comparable directional iperf tests and limits.

## Verified release

Runtime cc5d21d (GET10b8c85, path-preservation b7e8a32) pushed, Poland
fast-forward pulled; only subscription service restarted. Both services active,
public health HTTP200. 288 tests passed, one pre-existing datetime warning.
Public DNS Google/Cloudflare and flushed Poland resolver return151.241.137.174.
New node connected; valid certificate installed with renewal timer; nginx valid.
Real managed Reality exits151.241.137.174 HTTP200. Moscow->FI service tunnel
exits151.241.137.174 HTTP200; FI->Moscow exits85.198.101.79 HTTP200.
Full public CDN GET/header /api-test and /api-fin from Moscow both HTTP204.
Poland direct EE GET tunnel HTTP204; Poland CDN TLS fails curl35 before XHTTP.
This is an OPEN edge/source gate, not evidence of universal mobile bypass.
Owner-only EE/FI repaired links exported to local Temp ArcVPN-progressive-dev-xhttp.md.
No keys or UUIDs printed; old Germany links removed from that artifact.
Actual owner generated catalog: Auto, YouTube, FI, EE, Poland/NL(FI aliases),
Sweden(EE alias), five bypass choices using FI path. Auto and YouTube each have
exactly FI and EE physical mains. Old fake FI22201/22202 hosts disabled.
Moscow pool now EE_BRIDGE + FI_BRIDGE at newIP. No Germany restored.

Short directional iperf, same SPB endpoint, 3seconds/2streams (not a capacity
guarantee): FI upload169.2Mbps/download402.8Mbps, ping22.30ms; EE upload539.8Mbps/
download589.9Mbps, ping14.97ms. One FI upload port timed out; retry passed.
Keep FI and EE peers; no evidence to promote FI above EE. Evening/p95/load
testing remains open. Old FI server retained for rollback, not delivery.
Restricted rollback snapshots: finland-replacement-before.json,
cdn-get-before.json, fi-promotion-before.json on control plane; Moscow nginx
arc-guide-https.before-fi-replacement.conf. No rollback required.
