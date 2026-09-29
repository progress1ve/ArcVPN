# Current: durable ArcVPN node/CDN skills and context — 2026-09-29

Goal: create reusable repository skills for adding nodes and for honest
Multitest benchmarking. Record current, verified ordinary/CDN/bridge topology
in one non-secret operational reference and repair stale OPTIONS baselines.
Non-goals: deploy nodes, run more benchmarks, change Remnawave/CDN/DNS,
create admin-panel workers or alter subscription runtime.
Affected: `.agents/skills/`, node contract/references, benchmark method,
`docs/operations/`, context index/handoff. Acceptance: skill validation,
source-vs-record consistency, no secrets, no stale live OPTIONS instruction,
scope boundaries and owner-approval gates. Risk: overfitting a historical
release as permanent truth. Mitigation: dated snapshot + verify live state
and public contracts each future run. Rollback: revert documentation commit;
production runtime unaffected. Matrix: current code/stage/live health,
validator, diff/secret scan, docs-only production fast-forward.

Local evidence: both new skills passed `quick_validate.py`; inventory IPs,
Finland release stage and GET/header implementation match the dated snapshot.
No runtime files changed. Production pull and final Git evidence pending.

## Prior: FI RU repeat + admin node automation plan

Scope: repeat audited original russian-iperf3-servers on active FI only; preserve
raw terminal output and present verbatim results. Plan only for owner admin
node provisioning and benchmark workers, no runtime/UI implementation or skill
changes. Components to inspect: existing nodes.preflight API, provisioner,
RBAC, admin nodes UI, persisted job infrastructure, node route contract.
Acceptance: full terminal artifact or explicit failure, honest sent/received
semantics, post-test node health, written staged plan with secret storage,
job cancellation/recovery, real-tunnel publication gates and browser QA.
Risks: temporary test bandwidth/load, shared public test endpoints. Bound test
to 900s; no tuning/restart/topology changes; stop only diagnostic job if needed.
Plan remains a proposal, not authority to provision/publish nodes.

Passed: original FI RU module exit0/109s, terminal TXT/raw LOG delivered,
post-run remnanode running/nginx active, scoped architecture plan saved.
Evidence docs/operations/finland-ru-repeat-2026-09-29.md. FI Moscow5606Mbps;
do not infer permanent throughput or prioritize above EE from one test.
No runtime/skill changes; deployment is docs-only, no service restart needed.
Rollback not needed for diagnostic. Next: owner approval/revision of plan.

## Earlier repeat Multitest 5/6/9 with terminal artifacts

Owner wants full terminal output rather than rewritten tables. Scope FI/EE
comparison, sequential per-host Multitest modules5/6/9; review nested scripts,
bounded execution and preserve raw logs/clean readable text outside Git.
Identify actual Kazan/Moscow/Novosibirsk coverage; never relabel fallback cities.
No network tuning, production topology changes, skill changes or report upload.
Acceptance: six complete outputs or explicit failures, download/display files,
honest direction/city limitations, post-test health. Keep FI/EE equal peers.

## Prior completed Multitest benchmark

Owner requests actual Multitest first; skill changes explicitly deferred until
results and owner approval. Test active SSH-managed FI, EE, Moscow, Poland;
retired servers excluded, provider-managed Albania has no authorized SSH.
Use reviewed pinned Multitest Russian speed/IPQuality/short CPU modules,
privacy -p/-4 on IP checker, no report uploads, BBR/IPv6/network tuning or
production restarts. Preserve raw private logs and report missing tests honestly.
Upstream RU speed labels sent/received of one forward test as Upload/Download;
do not describe these as independent directions. Benchmark isn't tunnel gate.
Acceptance: per-host results/errors, source hashes, post-run health, concise
comparison and proposed skill update ONLY (no skill implementation).

Completed: four actual Multitest module runs + FI RU speed repeat. Full evidence
`docs/operations/multitest-2026-09-29.md`; method recorded in separate MD, not SQL.
No skill file changed, no runtime deploy/restart or tuning; both services active,
health200. Reports private. FI repeat NN4Mbps, Moscow unstable, SPB receiver0
invalid; no claims of universal clean IP or mobile bypass. Next: owner agrees
or revises proposed end-to-end node skill. No rollback needed for diagnostics.

## Completed: Finland replacement + all-user CDN GET

Runtime cc5d21d deployed and verified; 288 tests, both services active, health200.
Finland public DNS newIP, Reality/CDN/both Moscow SS tunnels passed. Actual
subscription has FI+EE Auto/YouTube, manual FI after YouTube; FI main bypass;
owner EE/FI link file updated. Keep equal peers: short speedtest favors EE.
Open: Poland-source CDN TLS failure and real mobile-operator verification;
evening/load speed tests. Detailed table/evidence/rollback:
`.codex/stages/finland-replacement.md`. Next: owner tests the two exported links.

## Prior completed broadcast stage

Owner request: add draft deletion; do not attach screenshots in replies.
Contract: delete buttons in history and saved-draft editor; confirmation names
that draft; cancel has no effect. Only draft status can be deleted atomically;
queued/running/stopped/completed campaign histories cannot be deleted. Soft
status deletion hides the draft, retains ledger and prevents test/edit/start.
Components: db_admin_broadcasts, owner API DELETE, ArcBroadcasts UI/demo.
Acceptance: status guard and API RBAC/origin tests; build; browser deletion of
agent-created demo draft, cancel and four responsive sizes; production visible
controls without deleting owner's drafts. No campaigns sent or bonuses granted.
Rollback: scoped revert, retained draft data can be restored operationally.

Passed: 37 campaign tests (delete, status guard, no re-test/edit/start, retained
ledger, owner/origin guards), TypeScript/Vite build, scoped Biome check.
Browser: agent-created demo draft cancellation and deletion verified; production
confirmation/cancellation verified at 390/768/1280/1600 without overflow. Local
evidence delete-draft-*.png / delete-production-*.png; not attached per owner.
Runtime d992578 pushed and Poland ff-only pulled. Subscription API service
restarted; both services active; public admin HTTP 200, anonymous DELETE 403.
No rollback needed. No owner drafts deleted; no sends/grants initiated by agent.
Latest live UI: outage campaign is stopped with 22 delivered of 24; earlier
compensation campaign remains a draft (63). These are owner-controlled actions,
not agent sends. Next: owner refreshes admin and deletes any unwanted draft.
# Netherlands alias follow-up — 2026-09-29

Owner-approved display-only Netherlands -> existing EE Reality/443, same
hostname/SNI/inbound, no CDN, multiplier1, unchanged URLs/UUIDs. No additional
automatic candidate. Release4d5049e deployed;286 tests, live equality and real
NL tunnel exit87.251.19.197 HTTP200 passed. Exact evidence/rollback:
`.codex/stages/netherlands-alias.md`. Future Poland/NL -> replacement FI deferred
until new node and direct Moscow route pass. Preserve existing broadcast work.
# Replacement Finland — 2026-09-29

Owner authorizes replacing old FI92.42.102.139 with151.241.137.174, restoring
original FI+EE peer plan, direct Moscow bridge, FI YouTube reciprocal egress,
same CDN resource and FI /api-fin; Poland/NL aliases use verified new FI.
Detailed acceptance, route table and rollback: `.codex/stages/finland-replacement.md`.
No extra Estonia relay, no Germany, no user UUID/URL/quota changes. Stage gates:
pinned SSH, target-generated unique Reality material, managed node connected,
real Reality/CDN/reciprocal SS tunnels, generated contracts, comparative speed.
