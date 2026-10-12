# HostUp allowance notification

Owner accepted: poll every12h, notify owner2075630349 once when remaining<=150GB; no50/20GB messages. Source HostUp current billing allowance, IP136.148.220.228, actual limit1024GB. No customer or routing changes.
Components: bot/services/hostup_bandwidth.py, main.py, settings persistent state; root-only ignored .secrets/hostup-monitor.env. No API key in Git/output.
Acceptance: real HostUp allowance response; threshold/dedup/restart/renewal/top-up/failure tests; bot startup; persisted next check12h. Actual low-allowance event conditional, no fabricated alert to owner.
Risks:12h polling delay explicitly accepted; provider API unavailable alerts after24h. Rollback revert module/start task; retain settings and protected credentials. Deploy commit/push/ffpull/restart bot only.

Verified2026-10-12:4 focused tests pass; production aiohttp API returns589.391GB used of1024GB,434.609GB remaining. Bot active; startup journal and DB state verify interval43200s and notified=false. No low-allowance message sent because threshold not reached. Real150GB crossing remains conditional; exact dispatch/dedup tested with fake Bot. API outage warning after24h only, no extra low-allowance thresholds.
Reviewed local commit d605fa59; Git HTTPS push unavailable. GitHub connector published identical tree0f17f49c713903660ad50fe729eec8dc85daa61e as8cf82ce1046cfd366a5f59bd305ecb0fb68c9525; production fast-forward pulled and only bot restarted. Credential600 remote .secrets/hostup-monitor.env, ignored; no key in commit. No rollback used. State persists in existing settings table; no migration. Local secret copy removed after remote verification.
