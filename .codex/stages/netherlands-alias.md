# Netherlands display alias — 2026-09-29

Owner requests Netherlands backed by Estonia now. After a replacement Finland
node is provisioned and verified, move Netherlands to that node and add Poland
backed by the replacement Finland. Future work is recorded, not activated on
the current broken Moscow/Finland route.

| Profile | Client/Host/SNI/inbound | Origin/CDN | Multiplier | Impact/failure/rollback |
| --- | --- | --- | --- | --- |
| Netherlands manual alias | exact existing Estonia Reality link, including its hostname, SNI and443 inbound | Estonia; no CDN | 1 | same credentials and subscription URL; not a real NL location or extra auto/YouTube candidate; revert alias tuple |

Components: subscription display alias and ordering tests. No node, DNS,
Remnawave, routing or quota mutation. Acceptance: exact EE connection payload
reused by NL; one EE automatic/YouTube main; generated live subscription shows
NL; services/public HTTP healthy. Preserve Germany retirement filter.

Release4d5049e pushed and Poland pulled ff-only; subscription service restarted,
both services active and public HTTP200. Fresh-main regression suite286 passed
(one existing warning); initial fresh-worktree collection needed initializing
its isolated empty SQLite schema, then passed. Live NL outbound equals EE,
AutoSelect/YouTube each retain one main. Real NL tunnel exits87.251.19.197,
ipifyHTTP200. No current Finland alias switch; replacement FI gate is deferred.
