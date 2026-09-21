# Referral activation, RU web gateway and bot artwork — 2026-09-21

## Goal

Ship the pending admin marketing/referral fixes, prevent referral-entry rewards
from being earned by accounts that never connect the issued subscription,
publish a Russia-hosted web entry point, and replace the main bot section
covers with one coherent ArcVPN visual system.

## Visible and runtime contract

| Surface | Contract |
| --- | --- |
| Referral entry reward | The inviter receives the configured entry/trial days only after the invited user's key is observed online with at least one device. Opening the bot or issuing a trial alone gives no days. Existing purchase reward behavior remains unchanged. The operation stays once-per-friend. |
| Referral copy | Bot and WebApp describe the entry reward as occurring after the friend connects ArcVPN on a device. |
| RU web entry | `https://ru.arccnet.space/`, `/app` and `/admin` expose the current production landing, cabinet and admin through the Moscow VPS. Existing `arccnet.space`, `panel.arccnet.space`, subscription URLs and API contracts remain unchanged. |
| Bot covers | Cabinet, payment, referral, settings and subscription screens use matching 16:9 dark navy/cold-blue ArcVPN covers, ArcVPN mark and exact Russian section title. No third-party mark or slogan. |
| Pending admin release | Marketing links/promocodes, campaign graph edges, trial classification and mobile current-server field from commit `55c9052` reach production. |

## Components

- Referral lifecycle: `bot/handlers/user/trial.py`, `bot/services/scheduler.py`,
  `bot/services/billing.py`, user referral copy and focused tests.
- Bot artwork and consumers: `bot/assets/`, start/settings, subscription,
  payment and referral handlers.
- Production control plane: `pl-control`, bot/subscription services and nginx.
- Russia gateway: existing `msk-beget` nginx listener behind its current HAProxy
  TLS route; no Remnawave, Reality or VPN transport change.

## Non-goals

- Do not change reward amounts, purchase rewards, UUIDs or subscription URLs.
- Do not move the database or bot runtime to Moscow.
- Do not change the primary domain DNS or node/VPN topology.
- Do not alter Telegram message text beyond referral-condition accuracy.

## Acceptance

- Trial issuance test proves no referral reward is invoked.
- First observed device connection invokes entry reward once and marks the key;
  later sync passes do not grant it again.
- Purchase reward tests remain green.
- Five final covers exist in the repository and each requested bot surface uses
  the intended asset with text fallback if a file is unavailable.
- Bot test suite and both frontend builds pass.
- Production fast-forwards to the release commit; only affected services are
  restarted and active afterward.
- Public primary and RU gateway landing, cabinet and admin return 200 and load
  their referenced JS/CSS assets.

## Risks and rollback

- A panel polling outage delays the reward; it must not grant on uncertain
  state. The next successful online observation retries naturally.
- Marking the connection before reward completion could lose a reward. Reward
  processing therefore runs before the durable `connect_notified` marker and
  is independently idempotent in `referral_stats`.
- The RU VPS has 1 GB RAM and already terminates VPN traffic through HAProxy.
  The web gateway uses the existing local nginx listener and adds no app
  runtime. Rollback restores the previous placeholder nginx site and reloads
  nginx.
- Code rollback is a Git revert followed by rebuilding static bundles and
  restarting only bot/subscription services.

## Verification matrix

| Check | Evidence target |
| --- | --- |
| Referral gate/idempotency | focused unit tests around trial provisioning and scheduler first-connect path |
| Artwork | image inspection, dimensions and actual handler references |
| Frontend/backend regression | Python tests, TypeScript checks, both Vite builds |
| Production | Git SHA, active services, bounded journals |
| Public web | external HTTP status, titles and referenced asset status on primary and RU URLs |
