# Marketing, referral graph and trial-state repair — 2026-09-21

## Goal

Restore the useful Growth workflows in the current admin: create and manage
advertising referral links and promocodes, display referral-link attribution in
the referral network, expose the user's current server on mobile, and stop
classifying trial access as a paid subscription.

## Non-goals

- No changes to referral rewards, tariff prices, subscription URLs or UUIDs.
- No deletion of campaigns, promocodes, payments, referrals or nodes.
- No node topology or Remnawave mutation.
- No new coupon, partner payout or broadcast subsystem.

## Components

- Backend: `subscription_api.py` campaign/promocode/referral/user endpoints.
- Admin adapters: `admin_webapp/src/arcvpn/api.ts` and referral network adapter.
- Admin UI: new compact Marketing page, admin routing/navigation, referral
  graph, user subscription detail and mobile layout.
- Tests: API contracts for campaign edges and trial classification; frontend
  model/component checks where practical.

## Visible contract

| Surface | Required behavior |
| --- | --- |
| Marketing | One page with Referral links and Promocodes tabs; lists existing entries; creates a link with name, optional code and entry/payment bonus days; creates fixed-RUB or percent promocodes with usage and lifetime limits; copies generated links/codes; toggles active state. |
| Referral network | Each advertising referral link is a campaign node. A `campaign → user` edge connects it to every directly attributed signup, alongside ordinary `user → referral` edges. Campaign counters and detail panel use real attribution data. |
| User list/detail | Trial keys are labelled trial even when their tariff row is Standard. Successful `trial`/`trial_start` payments do not make the user paid. |
| Mobile user detail | Subscription connection block always shows “Текущий сервер”; value comes from current Remnawave presence when online and falls back to the key/server record or “Не подключён”. No horizontal overflow at 390 px. |

## Acceptance

- Campaign and promocode create/list/toggle workflows work against ArcVPN API
  with validation and visible loading/error/empty states.
- Referral graph response contains real campaign nodes and campaign edges, and
  preserves existing referral edges.
- Active and expired trial keys map to `trial_active`/`trial_expired`; paid keys
  map to `paid_active`/`paid_expired`.
- User list, detail and referral network all agree on trial versus paid.
- Current server is visible at 390, 768, 1280 and 1600 px.
- Python/API tests, TypeScript checks/build and browser QA pass.

## Risks and rollback

- Incorrect trial inference could relabel historical access. Classification is
  tied to durable `trial_entitlements.vpn_key_id`, with payment-type fallback
  only for legacy trial records.
- Campaign graph expansion can become dense; existing 5000-edge cap remains.
- Rollback reverts this stage and rebuilds `admin_webapp_dist`; stored campaign
  and promocode rows remain valid and auditable.

## Verification matrix

| Check | Evidence |
| --- | --- |
| Backend classification and graph | focused pytest fixtures |
| Marketing create/toggle | local browser + API fixture |
| Mobile server visibility | browser at 390x844 and 768x1024 |
| Desktop graph/marketing | browser at 1280x900 and 1600x900 |
| Build/regression | admin Vite build and relevant Python tests |

## Result and evidence

- Marketing was added at `/admin/marketing`: both tabs, creation forms, copy,
  active-state toggles and empty/loading/error states were exercised locally.
- Referral-network browser evidence shows the campaign node connected to its
  attributed user and the campaign counter populated from backend data.
- User-detail browser evidence shows a trial badge and the current server in
  the subscription connection block.
- `python -m pytest ...`: 22 passed; one existing `datetime.utcnow()`
  deprecation warning remains.
- `npm run type-check`: passed.
- `npm run build`: passed; Vite retains the existing large-chunk warning.
- `biome check` reports no new errors; remaining notices are pre-existing
  warnings in shared API and subscription-detail files.
- The available browser driver did not expose viewport resizing, so exact
  390/768 pixel acceptance remains for a later device pass; the responsive
  one-column server block was verified in source and normal browser rendering.
- Production was not changed in this stage.
