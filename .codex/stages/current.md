# Stage: combined add-ons and payment UX (2026-09-03)

## Goal

- Move the WebApp add-on entry directly below `Создать свой тариф` and remove
  the separate active-cabinet action.
- Let one add-on order contain both a selected bypass pack and selected device
  count, with the same payment-method sheet used by subscription purchases.
- Add separate bot renewal buttons for device and bypass add-ons.
- At bypass exhaustion, show both website and bot purchase buttons.
- Reset `@Turan11627` bypass usage before implementation.

## Non-goals

- No tariff catalog price changes, subscription URL changes, UUID changes,
  responsive redesign, or add-on package price changes.

## Components

- `subscription_api.py`, database add-on persistence/fulfillment, WebApp API and
  purchase flow, bot renewal keyboards and scheduler notification keyboard.

## Albania topology contract

| Visible profile | Client host | CDN | Origin/fallback | Host/SNI | Inbound | Multiplier | Public URL impact | Failure/rollback |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Албания #1 | `al1-goykb.vpvr4ib84nuv6hdkt.ru` | none | direct Albania | same hostname | VLESS Reality/raw, 3342 | x1 | none | disable Host and remove from Auto |
| Албания #2 | `al1-goykb.vpvr4ib84nuv6hdkt.ru` | none | direct Albania | same hostname | Hysteria2/TLS, 3343 | x1 | none | disable Host and remove from Auto |
| 🇷🇺 Ютуб без рекламы | Netherlands + Albania | none | client-side least-load over the two countries | per child outbound | existing NL plus both Albania transports | x1 | unchanged subscription URLs | remove Albania children; keep existing Netherlands path |

- Customer order after Netherlands is Albania #1 then Albania #2. Both Albania
  transports join the main squad and the general Auto profile only after the
  RemnaNode connects. The YouTube row remains one visible profile and becomes a
  latency/load-aware selector over Netherlands and Albania.
- The node/profile is prepared hidden first. Its generated RemnaNode secret is
  stored only in a root-readable production `.secrets` file for WCloud entry;
  no private key or node secret enters Git, command output, or chat.

## Exact contract

- A combined order price is the sum of the authoritative bypass package and
  `25 RUB * device count`; either part may be zero but not both.
- The existing bypass packages remain 5/15/30/45/75/115 GB at
  20/35/60/90/175/290 RUB. Device quantity is a positive integer and the
  resulting entitlement may not exceed 15 devices.
- Fulfillment applies both components exactly once and synchronizes both panel
  identities before marking the order applied.
- Website notification opens `/app/?screen=addons`; bot notification uses a
  bot deep-link that opens the add-on choice without requiring typed input.

## Risks and rollback

- Risk: partial panel synchronization after payment. Mitigation: persistent
  order metadata, idempotent local application and `manual_review` on failure.
- Rollback: revert the stage commit, deploy by fast-forward and restart only bot
  and subscription services. The user counter reset has its own pre-change DB
  backup and is intentionally not reverted by a code rollback.

## Acceptance

- Target user's isolated bypass counter is reset in Remnawave and locally.
- WebApp placement, combined selection, summed server price and shared payment
  method sheet match the contract.
- Bot renewal and exhaustion keyboards expose the requested destinations.
- Focused/full automated checks and production verification are recorded before
  closeout; owner dirty files remain untouched.

## Current evidence

- `@Turan11627` bypass counter was reset in Remnawave and locally after a
  dedicated production database backup.
- Add-on runtime `b46c429` is deployed with schema v62; bot and subscription
  services are active. Per owner instruction, automated tests were not run.
  Python compilation and the Vite production build completed successfully.
- Albania profile/node preparation is deployed through `cd50e38`. The generated
  WCloud RemnaNode secret exists only in root-readable production storage and a
  user-readable local Downloads copy. The node is not connected yet, so no
  Albania Host or squad binding has been published.
- Catalog support and the Netherlands/Albania YouTube least-load profile are
  deployed at `a34c33e`; Albania children remain absent until the guarded
  promotion script observes a connected node. Public health is `OK` after the
  subscription restart.
- Remaining gate: enter the prepared secret and Poland panel IP in WCloud, then
  run `scripts/promote_albania_node.py` to create the two Hosts and attach both
  inbounds to the main squad. Do not bypass its connected-node check.
