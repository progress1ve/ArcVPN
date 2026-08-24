# Current stage: repository hygiene and Finland retirement

Status: complete

## Goal

Leave a reproducible, classified checkout for the next chat, activate encrypted access to current servers, and retire Finland without changing existing user subscription URLs or UUIDs.

## Acceptance

- Active credentials exist only as ignored DPAPI vault entries and can perform host-key-verified SSH.
- Finland catalog rows are disabled in production and generated profiles have a hard retirement filter.
- Obsolete screenshots, unused assets/components, duplicate/inactive units, staging probes, and retired 3x-ui mutation scripts are removed.
- Production and development dependency manifests exist; README matches the actual services and workflow.
- Python tests, WebApp build, diff checks, secret scan, deployment, service health, and public output are verified.
- Residual generated/editor state is ignored; retained tracked paths have an explicit class.

## Evidence so far

- DPAPI vault aliases: `pl-control`, `de-dhost`, `nl-dhost`; no plaintext values are tracked.
- Production systemd inventory confirms only the canonical bot/subscription/fleet/user-sync units are installed; removed staging/x-ui/generic units are inactive or absent.
- Production SQLite catalog rows for both Finland profiles were backed up and disabled.
- Local Python suite: 39 passed, including Happ JSON hidden-outbound retirement coverage.
- WebApp production build passes; existing Svelte accessibility/dead-CSS warnings remain UI debt for the next browser-first stage.
- Commits: `ccfde18` (hygiene and retirement) and `f5943cb` (filter retired nodes before Happ JSON generation).
- Production fast-forwarded to `f5943cb`; `arcvpn-subscription.service` is active, health returns `OK`, and a live active Happ subscription contains no Finland label, domain, or legacy address.

## Rollback

- Code cleanup: revert the resulting Git commit.
- Finland catalog: restore the timestamped pre-retirement SQLite backup or re-enable only the two audited catalog rows.
- Local vault: DPAPI files are machine/user-bound and are not part of Git rollback.

## Next stage

Run `$arcvpn-frontend-qa` as a browser-first admin-panel stage beginning with Support. Define viewport, interaction, accessibility, and screenshot acceptance before editing. Production still contains 64 pre-existing untracked operational backup/env files and one tracked `scripts/ssh_askpass.sh` override; they were preserved and must be handled only by a separate retention audit.
