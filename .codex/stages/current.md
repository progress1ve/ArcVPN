# Fleet outage and IP-block alerts — 2026-09-20

## Goal
Notify every configured ArcVPN administrator in Telegram when a production
RemnaNode is unavailable or appears unreachable from Russian networks, and send
one recovery notice when service returns.

## Contract
- The authoritative bot on Poland runs the check every 5 minutes.
- Each enabled registered RemnaNode is checked through Remnawave connectivity,
  a direct TCP probe from Poland, and TCP probes from up to three Russian
  Check-Host nodes.
- `server_down`: Remnawave is disconnected or the direct public TCP probe fails.
- `possible_ip_block`: the direct probe and Remnawave are healthy, at least two
  Russian probes completed, and no Russian probe can connect.
- External-probe failure or incomplete results are `unknown`, never an outage.
- Alert after three consecutive failures; recover after two consecutive healthy
  checks. Send once per transition, not every scheduler iteration.
- Messages contain node name, failure class, failed public ports, probe counts,
  first detection time, and a compact recovery duration. No secrets, UUIDs,
  subscription URLs, tokens, or private addresses are included.

## Components
- `monitoring/fleet_alerts.py`: bounded probes, state machine, SQLite persistence.
- `bot/services/scheduler.py`, `main.py`: periodic execution and Telegram delivery.
- `database/migrations.py`: persistent deduplication/recovery state.
- `tests/test_fleet_alerts.py`: classification, debounce and recovery coverage.

## Non-goals
- No automatic node restart, DNS change, failover, firewall or Remnawave mutation.
- No change to subscription URLs, UUIDs, inbounds or client routing.
- Hysteria/UDP is not judged by a TCP probe.

## Risks and rollback
- Check-Host is a third-party observation source; its outage must degrade to
  `unknown`. Public node host/port values are sent to that service.
- Three-failure/two-recovery hysteresis bounds false positives and alert spam.
- Rollback: revert the release commit and restart only `arcvpn-bot.service`.
  The added state table is inert and safe to retain.

## Acceptance
- Unit tests cover down, possible block, external unknown, debounce, dedupe and recovery.
- Existing fleet monitor tests remain green; Python compilation passes.
- A dry-run on production discovers enabled nodes without sending Telegram.
- Production deployment is fast-forward only; only the bot is restarted.
- Bot remains active and logs a successful fleet check without leaking secrets.

## Evidence
- `tests/test_fleet_alerts.py` plus existing fleet test: 7 passed.
- `py_compile` passed for monitor, scheduler, main and migrations.
- Check-Host node discovery currently returns three Russian probe nodes.
- Production dry-run discovered 7 enabled nodes and 3 Russian probe nodes with
  no Telegram event generated.
- Runtime release commits are `210c560`, `da31e6d` and final contention fix
  `31678ea`; production was fast-forwarded and only `arcvpn-bot.service` was
  restarted.
- Production schema is v63. A full live cycle completed with
  `nodes=7 events=0 external_nodes=3`; the bot remained active and no new
  `database is locked` entry appeared after the final restart.
- Both fleet monitors now finish network probes before opening SQLite, so they
  do not hold the shared write lock during remote requests.
