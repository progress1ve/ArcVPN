# BEDOLAGA admin operational modules — 2026-09-19

## Goal
Complete and deploy the direct BEDOLAGA admin migration for squads, payments,
sales statistics, traffic usage, tickets, and Remnawave. Every visible page
must use ArcVPN data and must not be a fake or "coming soon" surface.

## Routes and data contracts
| Route | Source of truth | Required behavior |
| --- | --- | --- |
| `/admin/payments` | ArcVPN `payments` + `users` | server search, status/method/period filters, paging, totals |
| `/admin/sales-stats` | ArcVPN payments/subscriptions | summary and trial/sale/renewal/add-on/deposit/payment-health tabs |
| `/admin/traffic` | ArcVPN main + LTE counters | search, status, sort, paging and both traffic classes |
| `/admin/tickets`, `/:id` | support threads/messages | queue, detail, reply, status change |
| `/admin/remnawave` | live Remnawave overview | connection, fleet, online, traffic, node health |
| `/admin/remnawave/squads/:uuid` | live internal squads | squad membership/inbounds/read-only detail |

## Components
- `subscription_api.py`: bounded read APIs and audited ticket status mutation.
- `admin_webapp/src/arcvpn/api.ts`: ArcVPN transport and normalized adapters.
- BEDOLAGA API modules for payments, sales, traffic, tickets and Remnawave.
- `ArcAdminRoot.tsx`: route wiring.
- Existing BEDOLAGA pages/components remain the presentation layer.

## Exclusions
- No destructive node/squad mutations, bulk migration, refund or payment replay.
- No fake campaign, provider, device or historical telemetry values.
- Preserve existing UUIDs, subscription URLs and active access.
- No customer Svelte cabinet or landing changes.

## Acceptance
- All six entry routes render live or explicit empty/error states; no adapter 404s.
- Payments filters and paging work; traffic displays main and LTE counters.
- Ticket replies and status changes use existing permission checks and audit.
- Remnawave connection, nodes and squads come from the authority response.
- Browser QA at 390/768/1280/1600: zero document overflow, reachable controls,
  readable tables/cards, no admin burger or redundant header label.
- Frontend build/tests and focused backend tests pass.
- Staged diff contains only the migration and documented support files.
- Commit/push, Poland production `pull --ff-only`, affected service restart, and
  authenticated/public verification complete.

## Risks and rollback
- Remnawave may be temporarily unavailable: pages show degraded/error state and
  never replace live data with demo data in production.
- Large tables are bounded and paginated; no unbounded DB or panel fetches.
- Roll back by reverting the deployment commit, rebuilding static assets and
  restarting only `arcvpn-subscription.service` if Python routing changed.

## Verification matrix
| Surface | Functional check | Viewports |
| --- | --- | --- |
| Payments | filters, totals, paging, user link | 390/768/1280/1600 |
| Sales | period + six tabs | 390/768/1280/1600 |
| Traffic | main/LTE sort and search | 390/768/1280/1600 |
| Tickets | list/detail/reply/status states | 390/768/1280/1600 |
| Remnawave | connection/nodes/telemetry | 390/768/1280/1600 |
| Squads | list/detail/empty | 390/768/1280/1600 |

## Evidence
- React production build: 2516 modules, completed successfully.
- Focused frontend tests: 10 passed; focused backend API tests: 3 passed.
- Browser routes verified: payments, sales statistics, traffic, tickets,
  Remnawave and squads. Desktop and 390 px checks report zero document overflow;
  browser console has no warnings or errors.
- Deployment and public verification remain pending.
