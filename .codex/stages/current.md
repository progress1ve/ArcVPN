# Current: React admin node operations and traffic usage — 2026-09-30

The parallel ordinary/LTE traffic slice has its own acceptance and evidence in
`.codex/stages/traffic-usage-today.md`; the node operations contract continues below.

Goal: truthful per-node detail, load/headroom alerts, Russian-city Multitest runs with history/comparison, and safe new-node onboarding from IP and credentials.

Non-goals: silently publish a node, alter existing URLs/UUIDs or active routes, run benchmarks or provisioning on production nodes during development.

Components: `admin_webapp` React, `subscription_api.py`, database migrations and monitoring; bounded worker for heavy jobs. Existing Svelte admin is not the live `/admin/remnawave` surface and is not migrated.

Acceptance:
- Live node detail reconciles active/retired inventory and Remnawave; shows role, status and freshness, users, CPU/RAM/network history, measured capacity, windowed p95 headroom and unknown state where evidence is insufficient.
- Capacity warnings expose their inputs and use sustained thresholds. A theoretical user estimate states its observed per-user assumption; no fixed count is invented from bandwidth alone.
- Multitest 5/6/9 uses pinned reviewed recipes, one heavy job per node, bounded resources and time, cancellation, raw logs, city/direction results, history and comparison. Missing results remain missing.
- Preflight pins SSH host key, validates target and existing services; encrypted secrets remain outside Git/DB and never return via API. Durable jobs use idempotent reconcile, hidden canary and real-tunnel gates. Publication is separate and requires an exact accepted route table.
- React browser checks at 390/768/1280/1600, including loading/empty/error/focus states; backend/build checks pass.

Owner choices: full preset = ordinary node, reciprocal Moscow bridges, YouTube, autoselect and CDN. Password may be held in a server-side encrypted vault, never redisplayed; require controlled expiry/deletion policy. Exact path/host/SNI/order table must be previewed and accepted before topology mutation.

Visual contract from owner reference: one node detail with identity/status header and functional tabs. Overview holds current readings, fleet-sampled 24-hour availability, services and events; Metrics holds period controls and CPU/RAM/disk/network graphs; Services holds real Remnawave inbound/CDN facts; Performance holds observed p95 and confirmed headroom. Logs and LTE Availability appear only when records exist. Use ArcVPN React colors and existing SVG icon set, hide horizontal scrollbar, keep missing/stale states explicit. The redundant page-refresh button was removed. Reference screenshots guide hierarchy and density, not literal claims about installed services.

Additional LTE/SDN contract: three scheduled mobile-operator checks per day for T2, T-Mobile, MegaFon, Beeline and MTS. Store operator, region, probe type, endpoint, time, outcome and reason separately. A TCP/TLS probe may establish network reachability but cannot prove a VPN client profile works under restrictions. Label this separately from a real client tunnel gate, and require evidence that the operator probe ran during a restricted/whitelist period before declaring bypass usable. Confirmed failure/recovery goes through the existing Telegram fleet-alert pattern with independent state per node/operator/path; unavailable probes remain unknown, not failed. External LatencyLab API shape and commercial limits await documentation. Never include its key in Git, logs or API calls from the browser.

Owner UI correction: node detail uses tabs. Overview = now, availability, services and recent events. Metrics = period and graphs. Services = actual inbounds, subscription/balancer membership and CDN route. Performance = capacity plus Multitest. LTE = operator history. Logs and Security expose only collected facts with explicit missing states; no decorative fake service health. Owner supplied a private old OPTIONS and new GET XHTTP pair as negative/positive regression examples. Their shared identity must never be committed. The provided LatencyLab run reports old failed on four operators and new passed on three; MegaFon is not established by that new run. Re-run through the final integration once its API contract is known.

Risks: stale Remnawave inventory, uncertain per-user bandwidth, active-traffic disruption from tests, leaked credentials, partial provisioning. Mitigation: reconcile sources, show unknowns, load/cooldown gates, pinned SSH, encrypted vault, locks and explicit publish. Rollback: revert React/API release; retain job ledger for controlled recovery; never automatically delete unknown resources.

Verification matrix: source/API reconciliation, calculation tests, RBAC/origin/SSRF/host-key/restart tests, pinned-script hashes, worker cancellation on a test VPS, browser viewport evidence, production checks after deployment.

Baseline: `origin/main` d7d9ca5. Primary checkout dirty and behind; clean detached checkout selected. Live `/admin/remnawave` is React and listed Estonia, retired Germany and Moscow but no Finland. Roadmap describes Svelte preflight, which is not this live UI. Existing Flask preflight disables host-key checking. No production mutation or benchmark/provisioning run.

Progress (2026-09-30): React tabbed node detail, real metrics/capacity/events/registry/LTE read APIs, fleet availability samples with unknown gaps, truthful Finland/Estonia mapping, and SSH fingerprint-pinned read-only preflight are implemented locally. Both webapp builds pass; the full Python suite passes (301 tests). Browser checked at 390/768/1280/1600px; 390px has no horizontal page overflow. The Multitest source was reviewed: choices 5/6/9 execute additional remote shell scripts, so the owner's curl command cannot be a safe production recipe. No benchmark worker or tested LatencyLab adapter exists yet. The owner confirmed no test VPS is available now and installation testing will wait. The owner authorized production release once the requested functionality is ready; this incomplete stage is not deployed.
