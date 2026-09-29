# Generic device repair — 2026-09-29

Goal: prevent unrecognized public subscription probes from creating or restoring
device slots; verify @sso095 retains the active INCY device.
Components: subscription_api.py, subscription regression tests, scoped DB repair.
Acceptance: generic unbound GET cannot register/adopt/reactivate; HEAD remains
read-only; recognized clients and bound aliases retain access and slot limits;
verified synthetic generic rows no longer consume slots; key IDs/URLs unchanged.
Contract: unbound generic requests without HWID receive the existing legacy
reimport response; explicit import and valid device aliases keep existing behavior.
Non-goals: UI, topology, other unfinished stages. Primary owner files untouched.
Risk: unidentified clients must use explicit import; bound profiles remain valid.
Rollback: revert scoped commit and restart subscription API; restore only repaired
device activation flags from restricted backup if necessary.
Verification: focused route tests, full Python suite, production service/health,
real database counts and repeated generic probes without outputting URLs or IDs.
Status: complete. Runtime commit `a5efeb4` pushed to main and Poland ff-only
pulled. Only subscription service restarted; active, public health 200.

Acceptance evidence:
- All 279 Python tests passed; final focused 18 tests passed after test cleanup.
- Staged diff reviewed and whitespace check passed; repair script compiled.
- Repair dry-run verified one active synthetic row and zero unmatched rows;
  applied after DB backup created with mode 0600. One row deactivated, no row
  deleted, all key IDs/URLs/UUIDs identical before and after.
- Public generic requests with Mozilla, curl and TelegramBot agents returned
  200 with existing reimport response; all device IDs/activation/hash fields
  unchanged after requests. No active generic unknown rows remain globally.
- sso095 has exactly one active INCY iPhone 14 Pro; its real public bound
  subscription returned 200 and contained the existing UUID.
- HEAD, recognized client recovery, stable HWID recovery and generic bound
  alias access passed regression checks.

Rollback not needed. Residual: unknown unbound clients must explicitly import;
existing bound aliases remain supported. No frontend or protocol changes.
Next: user refreshes Devices screen; no further server action required.
