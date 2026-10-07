# Sweden CDN publication — 2026-10-07
Owner authorizes production publication, superseding private-tests-only boundary.
| Profile | Client host / CDN / group | Origin / backup | Host/SNI | Path / inbound | Multiplier | URL impact | Failure / rollback |
|---|---|---|---|---|---|---|---|
| Auto, Best Bypass, #2,#5,#8 | cdn-de.arccnet.space / existing / ee-origin | Sweden136.148.220.228 / none | same | /api-se-test-4096 10012 then /api-se-test-24000 10013 |1|none|SE61/EE39 then CDN4096/7 XMUX then CDN24000/10 then block; revert runtime/panel snapshot|
| #3 | same | same | same | /api-se-test-4096 10012 |1|none|XHTTP4096/7 XMUX only, no balancer; same rollback|
| #4 | same | same | same | /api-se-test-24000 10013 |1|none|XHTTP24000/10 GET header only; same rollback|
| #6 | same | same | same | /api-se-65536 10014 |1|none|XHTTP65536/60–75 GET header; body variant failed CDN but passed origin; header variant passed 1MiB upload; same rollback|
| #7 | same | same | same | /api-se-32768 10015 |1|none|XHTTP32768/10 GET header only; same rollback|
| Subscription/import and old imported CDN | existing host/resource/group | Sweden forwarding to Poland for subscription / Estonia for old paths | correct upstream Host | /sub,/import,/api/device/import,opaque-ID; /api-test,/api-ee-direct,/api-ee-reserve |1 or n/a|none|preserve refresh and previously issued clients; origin config snapshot rollback|
Acceptance: four real CDN tunnels from Moscow and generated owner profiles; local focused tests/syntax; stable UUIDs/URLs/order; commit/push/ff-pull, subscription-only restart, service/public checks. No repeated throughput suite. Physical Happ and Kazan throttling owner gate; Poland CDN regional timeout remains. Server/Remnawave necessary additions authorized as part production publication. Ordinary locations/YouTube/RUbridge remain61/39.

Prepublication evidence:26 focused tests passed;16 generated configs Xray syntax passed;four real test CDN tunnels from Moscow passed. Body65536/60-75 raw origin204 but CDNtimeout; same requested size/interval switched to header, get and1MiB upload204. Existing node inbound IDs preserved and allfour authorized for existing LTE squad. Nginx syntax passes, old-path proxy Estonia and uncached subscription proxy Poland retained.
Four generated customer profiles #3/#4/#6/#7 passed actual CDN HTTP204 from Moscow with existing customer LTE authorization; standalone routing gate passed.
