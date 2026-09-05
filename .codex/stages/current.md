# Stage: combined add-ons and payment UX (2026-09-03)

## 2026-09-05: Estonia public IP replacement

Owner acceptance: replace Estonia origin `95.85.245.23` with `95.85.249.187`; keep every public subscription URL, UUID, hostname and Reality identity unchanged.

| Visible profile | Client hostname | CDN resource | Origin group | Active/backup origin | Host/SNI | Inbound/path | Multiplier | Public URL impact | Failure/rollback |
|---|---|---|---|---|---|---|---|---|---|
| Estonia | `ee.arccnet.space` | none | none | `95.85.249.187` | existing Reality values unchanged | existing VLESS Reality | x1 | none | restore DNS and Remnawave node address to `95.85.245.23` |
| Best bypass CDN fallback | existing CDN hostname | existing Yandex resource | existing Estonia/Netherlands group | Estonia `95.85.249.187`, Netherlands reserve | unchanged | existing XHTTP `/api-test` | x1 | none | restore Estonia origin IP only |

Acceptance: DNS and every literal Estonia origin reference use the new IP, RemnaNode is authorized and connected, a fresh generated client profile retains the stable hostname/UUID, and real tunneled traffic succeeds from Russia. Rollback is the old IP in DNS, Remnawave and inventory.

Result at `8b1f9d0`: the Estonia guest primary address, Remnawave node/Host records and repository inventory are `95.85.249.187`; Remnawave reports the node connected. REG.RU authority and the Yandex origin were cut over by the owner, and the old address was removed from the guest/runtime. A fresh public profile publishes `95.85.249.187`, VLESS Reality TCP and `fp=firefox`; its credential-safe real HTTP canary from Russia returned 204. The deployed YouTube least-load profile over Netherlands and Albania also returned 204 and selected Albania during the final canary. Multitest to five Russian locations measured 490-1077 Mbps download, 503-1093 Mbps upload and 15-49 ms latency. Production subscription service remains active. All five bypass profiles and the general Auto profile contain Albania among their main candidates; YouTube contains Netherlands and Albania. Client-side Xray leastLoad observes reachability/latency, not Remnawave online-user counts, so panel occupancy does not affect selection in the current implementation.

## 2026-09-05: remove Hysteria and repair Estonia/YouTube

Owner acceptance: remove every Hysteria customer connection; retain stable subscription URLs and UUIDs.

| Visible path | Desired transport | Auto/selector membership | Public URL impact | Failure/rollback |
|---|---|---|---|---|
| Estonia | VLESS Reality only | main Auto | none | restore previous release |
| Netherlands | VLESS Reality only | main Auto + YouTube | none | restore previous release |
| Albania | VLESS Reality only | main Auto + YouTube | none | restore previous release |
| Germany | VLESS Reality only | main Auto | none | restore previous release |
| YouTube without ads | Netherlands VLESS | dedicated simple profile | none | restore prior selector |

Acceptance: no Hysteria URI/outbound in fresh public output; Estonia and YouTube must be checked through real tunneled traffic. Existing bypass XHTTP x1 paths are unchanged.

### Proposed Russian-route repair awaiting owner acceptance

| Visible profile | Client endpoint | Relay/upstream | Host/SNI | Inbound | Multiplier | Public identifiers | Failure behavior | Rollback |
|---|---|---|---|---|---|---|---|---|
| Estonia #1 | `nd.arccnet.space:8443` | Netherlands TCP relay -> Estonia `:443` | Host `nd.arccnet.space`, SNI `google.com` | existing Estonia Reality | x1 | subscription URL and UUID unchanged | profile fails if NL relay or EE upstream fails | restore Host endpoint to `ee.arccnet.space:443`, remove relay |
| Albania #1 | `nd.arccnet.space:8444` | Netherlands TCP relay -> Albania `:3342` | Host `nd.arccnet.space`, SNI Albania server name | existing Albania Reality | x1 | subscription URL and UUID unchanged | profile fails if NL relay or AL upstream fails | restore Host endpoint to Albania direct, remove relay |
| YouTube without ads | both endpoints above plus NL direct | Xray leastLoad over NL direct and relayed Albania | per child outbound | existing Reality inbounds | x1 | subscription URL and visible label unchanged | fixed fallback is NL VLESS, never direct | revert generated profile |

Evidence: from the local Russian network, Netherlands tunneled HTTP returned 204; Estonia stalled after TCP dial and even SSH did not deliver a banner, while Poland reached both Estonia services; Albania `3342` was unreachable locally but reachable from Poland and Netherlands. Netherlands has free ports 8443/8444, `systemd-socket-proxyd`, reachable upstreams, and UFW available. No topology mutation has been made for this relay proposal yet.

Result: production main squad has no Hysteria inbound, six active Hysteria Hosts were disabled, and the declarative squad list was updated with a backup. Fresh public plain/Happ output contains only VLESS. Server-side canaries passed, but owner-device Happ still failed on Estonia and the composite YouTube selector; Estonia therefore uses the documented Edge fingerprint fallback and YouTube is reduced to a simple Netherlands VLESS profile. Rollback is the pre-change environment backup plus re-enabling the disabled Hosts and reverting the release.

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
