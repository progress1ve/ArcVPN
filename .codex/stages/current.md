# Current stage: repository hygiene and Finland retirement

Status: verification and deployment in progress

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
- Local Python suite: 38 passed.
- WebApp production build passes; existing Svelte accessibility/dead-CSS warnings remain UI debt for the next browser-first stage.

## Rollback

- Code cleanup: revert the resulting Git commit.
- Finland catalog: restore the timestamped pre-retirement SQLite backup or re-enable only the two audited catalog rows.
- Local vault: DPAPI files are machine/user-bound and are not part of Git rollback.

## Remaining gate

Commit and push, safely fast-forward the dirty production checkout without deleting its classified backups, restart only `arcvpn-subscription.service`, then verify health and public catalog output.
