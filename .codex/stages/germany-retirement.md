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

## Release and evidence

- Runtime d1a3c32:233 tests passed, one existing datetime warning; compilation
  and staged diff check passed. Local Git DNS failed, recovered using a
  one-command curl DNS pin and Windows schannel; push succeeded. Poland pulled
  fast-forward and only subscription service restarted; bot/subscription active,
  public site HTTP200. Bundle staging was attempted but remote push had no
  credentials; no bundle-based deployment bypass was performed.
- Six Germany Hosts disabled; existing CDN /api-test Host rebound to EE's
  managed XHTTP inbound and node. No user UUID/URL/quota rotation or deletion.
  Restricted panel backup: /root/ArcVPN/backups/germany-retirement-before.json.
- Moscow EU_BRIDGE selector now EE_BRIDGE only; DE_BRIDGE removed. Inbound
  bindings reconciled if panel regenerated IDs. Finland remains excluded.
- nginx upstream arc_xhttp_eu now EE87.251.19.197:80 only; syntax/reload passed.
  Backup:/opt/arcvpn/staging/ru-arccnet.before-germany-retirement.conf.
- Three live JSON subscriptions: AutoSelect, YouTube, manual FI, EE, Sweden,
  five bypass profiles; Germany/Poland/Netherlands absent, no DE endpoint.
- Real XHTTP direct EE and Moscow origin HTTPS:Google204 from Poland.
  Full public CDN from Moscow:ipify200 exit87.251.19.197 and Google204, both
  legacy body and current HEADER2048/X-Data transports. This proves the
  accepted CDN -> Moscow -> EE route with managed authorization.
- Full public CDN from Poland repeatedly reset TLS or timed out, despite same
  identity passing direct origin. Source/edge-specific cause unproven; do not
  claim universal CDN/mobile-operator acceptance. No speculative transport
  or CDN resource changes applied.
- FI -> Moscow443 and Moscow -> FI80/2443 still fail. No FI promotion or
  conditional benchmark performed. Manual FI retains the previously disclosed
  broken YouTube->RU policy; its full readiness remains unaccepted.

Rollback restores exact panel/nginx backups and reverts scoped runtime commit,
but returned Germany must not be re-enabled without explicit owner direction.
Next step: resolve FI direct provider route, and separately validate CDN from
owner's mobile operator; existing EE is the only automatic main.
