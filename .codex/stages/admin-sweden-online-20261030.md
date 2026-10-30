# Admin Sweden visibility and Online — 2026-10-30

Completed and deployed runtime82ef7846307cb77338e9ffdbbae84f8b31392f2c. Owner requested Sweden on Remnawave Nodes and Online instead of cabinet version on admin home.

## Changes

Sweden was present and connected in authoritative Remnawave, but omitted by the UI's Estonia/Lithuania address filter. Added136.148.220.228 to that existing filter. Its normal card now shows the Sweden flag, HostUp provider, actual presence/status/traffic and existing statistics link; visible-node summaries include all3 nodes. No node provisioning/routing/catalog/UUID/URL/quota/authorization changes.

Home third desktop info card now shows unique customers online from authoritative remnawave.online_users, already deduplicated across main/LTE identities. Existing observation window3minutes. Known0 remains0; absent/unhealthy telemetry displays--. Mobile also includes Online, retaining other metrics. Existing60s polling now receives fresh values: replaced permanent shared overview cache with10s lifetime, concurrent read reuse and rejection eviction. No package/lock/dependency changes; current React admin retained, customer Svelte unchanged.

## Verification

-5frontend tests passed: unique customers vs sessions, known0 vs unknown, concurrent cache sharing/expiry/retry. TypeScript and production Vite build passed with Node24.22.1/exact npm-ci lock; existing large-chunk/static-dynamic import warnings only.
-Before screenshots reproduce version card/Sweden absent. Candidate built assets with real authenticated production API, then deployed public UI each passed360/768/1280/1600 home+nodes, Sweden statistics navigation, and isolated0/unavailable response fixtures.11checks each,no runtimeJS errors/horizontal overflow. Live screenshots show3nodes/2online/1offline and16online customers at capture; values naturally change. Existing narrow card-title truncation retained; statistics link has complete accessible name.
-HTTP root/app/admin/health200; new+previous mainJS/CSS200; anonymous admin overview403. Subscription restarted after Poland FFpull; bot remained active. Existing hashed assets retained for loaded clients. Backend/source topology untouched.
-Native Computer Use stopped because Chrome URL could not be recognized; isolated headless application test browser provided live evidence. Initial test harness teardown callback was repaired and clean reruns passed. A broader unrelated legacy backend test attempt had absent local Flask and a stale Estonia-vs-Lithuania operator assertion; those are not frontend acceptance, and no unrelated backend edits were made.
-Normal existing-owner credential login used temporarily for browser QA; logged out, temporary browser state copies removed locally/remotely. No credentials in committed evidence. Candidate/live JSON, HTTP evidence and before/after screenshots in evidence/admin-sweden-online-20261030/.

## Deployment and rollback

Runtime82ef7846 committed/pushed to main, Poland217.60.33.38 /root/ArcVPN FFpulled, subscription restarted, bothbot/APIactive. Publicreadback passed. Rollback scoped source/build revert and FFpull, subscription restart if needed; noDBrestore. Documentation closeout requires FFpull only. Owner reloads admin page to load current bundle.
