# HostUp allowance notification

Owner accepted: poll every12h, notify owner2075630349 once when remaining<=150GB; no50/20GB messages. Source HostUp current billing allowance, IP136.148.220.228, actual limit1024GB. No customer or routing changes.
Components: bot/services/hostup_bandwidth.py, main.py, settings persistent state; root-only ignored .secrets/hostup-monitor.env. No API key in Git/output.
Acceptance: real HostUp allowance response; threshold/dedup/restart/renewal/top-up/failure tests; bot startup; persisted next check12h. Actual low-allowance event conditional, no fabricated alert to owner.
Risks:12h polling delay explicitly accepted; provider API unavailable alerts after24h. Rollback revert module/start task; retain settings and protected credentials. Deploy commit/push/ffpull/restart bot only.
