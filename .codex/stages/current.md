# Moscow budget replacement — 2026-10-27

Owner accepted complete route scheme in chat: main website/cabinet and Moscow bridges move from unpaid85.198.101.79 to95.182.120.237; Poland remains control/API/bot/Telegram WebApp; CDN origin stays Estonia. No subagents; economy. SSH console fingerprint verified exactly SHA256:wO+t2tI3A40cU/pN5C/GIrHe0vNqwzI2/VIEGUQ0kRA, credential DPAPI aliasmsk-budget. Old host times out; not a rollback target.

| Client profile/path | Host/SNI | CDN resource/group | Active/backup | Inbound/path | Multiplier/URL impact | Failure/rollback |
|---|---|---|---|---|---|---|
| Website and browser cabinet | arccnet.space HTTPS | none | newRU95.182.120.237; API onPL217.60.33.38 | nginx localTLS8444 behind SNI443; root/app static, API/admin toPL | no subscription changes | preserve PL copy; oldRU unavailable; DNS switch after local HTTPS gate |
| Moscow bridge | ru.arccnet.space | none | newRU -> existingEE87.251.19.197 | Reality10443 behindSNI443; existingSS EE2443 | 1; URLs/UUID preserved | retain existing node/profile/inbound IDs; fresh node Reality keys require refreshed clients; no unpaidRU fallback |
| Estonia over RU pass-through | ee.arccnet.space SNI onru hostname8443 | none | newRU ->EE443 | TCP/SNI passthrough | 1; URLs unchanged | verify existing host8443 path; no old Germany |
| YouTube no ads | internalru.arccnet.space2444 | none | EE ->newRU direct | managedSS2444 allowed fromEE only | 1; preserve service authorization | real YouTube gate before final acceptance; do not assume tiny204 proves video |
| CDN bypass/Best | cdn-de.arccnet.space / Hostorigin.arccnet.space | bc8r4rihi5cxxmbj3qgs/ee-origin | EE87.251.19.197 only | existing10012–15 and paths | unchanged | no origin migration; DNS origin name alone is not configured origin |
| Bot/API/TelegramWebApp | existing Polish URLs | none | PL217.60.33.38 | existing | unchanged | preserve actual current bot URL |

## Evidence and prep

Live Yandex source group read in browser: sole87.251.19.197, HTTP, Hostorigin.arccnet.space. DNS arccnet/ru/origin stillold85.198.101.79; sub pointsPL; authoritativeNS Reg.ru. Remnawave Moscow disconnected, notdisabled; existingRU_VLESS_REALITY10443 andRU_SS_YOUTUBE2444, EE outboundYOUTUBE_RU pointsru hostname. Polish runtime7135cd90.
New host225218.msk.web.highserver.ru, Ubuntu24.04/kernel6.8, KVM1BroadwellvCPU/961MiB/20GBdisk/511MiBswap; onlySSH beforeprep; directCloudflarelocRU, YouTube204 reachable. OfficialUbuntu packages installing Docker/nginx/haproxy/ufw/fail2ban/certbot; no SSH restart or OS upgrade/reboot.

## Acceptance/risks

Before external switch: correct committed static release, valid main-site certificate, APIproxy upstreamTLSverify, Google verification file, admin/assets, frontend unchanged. TLS renew helper must not retain hardcodedoldIP. Scoped firewall: SSH recoverable,80/443/8443 public,22600 onlyPL,2444 onlyEE; no open proxy. BBR/fq if available, bounded logs. Preserve node/profile/inbound UUIDs and customer catalog/traffic identities; fresh own Reality key generated onnewRU.
Check actual SSYouTube egress/newRU, RU->EE tunnel andpassthrough, HTTPS root/app/admin/API, monitoring enrollment/heartbeat, cert timer, service health/RAM. NewRU tiny204 isn't fullvideo test; restricted/mobile and sustained load gates remain explicit. No broad benchmark.
DNS changes need authorizedReg.ru access or owner updates after readiness; do not repoint before newsitepasses. OldRU cannot rollback; keep PL authoritative code/static and protected scoped snapshots, stage-owned newhost filesbackedup before edits. No restoring customer database.
