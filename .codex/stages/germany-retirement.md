# Germany retirement and conditional Finland admission — 2026-09-29

Owner returned Germany and explicitly requests removal of Germany-backed
profiles. Finland admission remains conditional on a working direct Moscow
bridge; additional Estonia hop remains rejected.

| Profile | Client/CDN | Origin and route | Host/SNI and inbound | Multiplier | Identifiers/failure/rollback |
| --- | --- | --- | --- | --- | --- |
| AutoSelect and YouTube | existing EE Reality endpoint; existing CDN emergency only in AutoSelect | EE only until FI bridge passes; remove DE and DE-backed aliases | existing EE SNI/443 | 1 | URL/UUID unchanged; no DE fallback; revert scoped code |
| Existing bypass | cdn-de.arccnet.space, same resource/ee-origin | Moscow -> EE only, no returned DE | client cdn-de; origin origin.arccnet.space; /api-test -> EE10001 | 1 | same URL/UUID/LTE identity; fail closed if EE unavailable; restricted panel/nginx backups |
| Finland manual | fin.arccnet.space | unchanged; FI -> Moscow still fails | existing unique Reality/443 | 1 | no automatic/CDN promotion until actual tunnel passes |

Components: subscription catalog, Remnawave Hosts/Moscow outbound selector,
Moscow nginx upstream, focused tests and live managed CDN tunnel. Do not delete
users, squads, credentials, or returned server data. Disable delivery rather
than destructive panel deletion. Backup before mutation.

Acceptance: no DE or DE aliases in generated JSON/plain; EE and active
authorization preserved; managed CDN real HTTP204 and EE exit; services/public
HTTP healthy. FI direct HTTP/bridge ports still fail on today's recheck, so
conditional FI additions and benchmark are deferred, not passed.
