# Fleet alert false-positive correction — 2026-09-20

## Goal
Stop false Telegram fleet alerts, exclude retired/non-client-facing RemnaNodes,
and display incident time in Moscow time.

## Confirmed cause
- Remnawave still returns retired Finland, Finland LTE and Albania records as
  enabled. The Moscow bridge is not a directly client-facing VPN node.
- The classifier declared a node down whenever the Poland TCP probe failed,
  even when Remnawave and all three Russian probes confirmed it reachable.
- Stored timestamps are UTC and the message printed the raw value.

## Contract
- Exclude exact retired/non-client-facing names: ArcVPN Finland, ArcVPN Finland
  LTE, ArcVPN Albania WCloud and ArcVPN Moscow Bridge.
- A connected panel node with at least two completed external probes and any
  external success is healthy even if the control-plane TCP probe is blocked.
- `server_down` requires panel disconnect, or failure from both the Poland probe
  and all sufficiently complete external probes.
- An incomplete external result plus a failed direct probe is `unknown`.
- Keep regional-block detection: direct probe succeeds while zero of at least
  two Russian probes succeeds.
- Telegram renders the first-detection timestamp in Europe/Moscow with `МСК`.
- Clear only `fleet_alert_state` during rollout so false incidents do not emit
  recovery spam. Do not change node topology, subscriptions or user access.

## Acceptance
- Focused tests cover external confirmation overriding a local failure,
  incomplete evidence, retired-node filtering and Moscow-time formatting.
- Production checks only the current client-facing set and emits no event for
  the current healthy state.
- Bot remains active; no new fleet alerts or SQLite-lock errors occur.

## Rollback
Revert the correction commit and restart only `arcvpn-bot.service`. The cleared
alert state will rebuild safely from subsequent checks.

## Evidence
- Focused fleet tests: 11 passed; Python compilation and diff checks passed.
- Runtime commit `b140213` was pushed and production pulled it fast-forward.
- Only `fleet_alert_state` was cleared; `arcvpn-bot.service` alone was restarted.
- First production cycle completed with `nodes=3 events=0 external_nodes=3`.
  Estonia and Netherlands were healthy; incomplete evidence for Germany did not
  create an alert. Bot is active and no new SQLite-lock error appeared.

## 2026-09-21 Netherlands delivery retirement

| Visible profile | Client hostname | CDN resource | Origin group | Active / backup | Host and SNI | Inbound and path | Multiplier | Public URL impact | Failure behavior | Rollback |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Netherlands normal profiles | removed from customer delivery and AutoSelect | none | none | none | no control-plane change | no node configuration change | 1 | stable subscription URLs and user UUIDs; NL rows disappear after refresh | no NL route is offered; AutoSelect uses remaining main nodes and CDN only as fallback | revert the catalog filter |
| YouTube without ads | same ordinary main-node set as AutoSelect | none | none | ordinary direct nodes only | unchanged client hostname | unchanged normal profiles | 1 | same profile label; no subscription identifier changes | no CDN fallback is configured | revert the YouTube balancer generation |

- Owner authorization: remove Netherlands from the subscription because the VPS is no longer needed.
- Acceptance: no native or fallback subscription link resolves to Netherlands; Happ AutoSelect has no Netherlands outbound; the YouTube profile has the same ordinary main candidates as AutoSelect and no fallback; no UUID or subscription URL changes. No Remnawave, node, bridge, DNS or CDN mutation is in scope.
