# Estonia-only LTE alerts evidence — 2026-10-02

Owner explicitly requested Estonia-only scheduled bypass notifications. Removed Finland from worker targets and required native links, added notification host allowlist to discard stale Finland events, aligned quota to three scans. Existing Estonia /api-test and thresholds/cadence preserved. No topology or subscription changes.
Local: 7 focused tests passed (LatencyLab client/worker and alert state machine). Runtime deployment uses ff-only pull on Poland; oneshot monitor picks new code next invocation, no bot/subscription restart required. Rollback: revert runtime commit. Historical Finland database rows retained.
