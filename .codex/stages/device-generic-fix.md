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
Status: investigating; sso095 generic already inactive, INCY active.
