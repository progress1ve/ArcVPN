# Temporary public location aliases — 2026-09-21

## Goal

Show four temporary location rows to every subscriber to evaluate the visual
catalog before purchasing physical VPS capacity. These are display aliases, not
claims of independent physical exits.

## Accepted public contract

| Visible profile | Client hostname | CDN resource | Origin group | Active / backup | Host and SNI | Inbound and path | Multiplier | Public URL impact | Failure behavior | Rollback |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 🇵🇱 Польша | existing Germany endpoint | none | none | Germany only | unchanged Germany Reality SNI | existing Germany VLESS TCP | 1 | stable URL/UUID; one added row | fails with Germany | remove alias mapping |
| 🇳🇱 Нидерланды | existing Germany endpoint | none | none | Germany only | unchanged Germany Reality SNI | existing Germany VLESS TCP | 1 | stable URL/UUID; one added row | fails with Germany | remove alias mapping |
| 🇫🇮 Финляндия | existing Estonia endpoint | none | none | Estonia only | unchanged Estonia Reality SNI | existing Estonia VLESS TCP | 1 | stable URL/UUID; one added row | fails with Estonia | remove alias mapping |
| 🇸🇪 Швеция | existing Estonia endpoint | none | none | Estonia only | unchanged Estonia Reality SNI | existing Estonia VLESS TCP | 1 | stable URL/UUID; one added row | fails with Estonia | remove alias mapping |

## Scope and acceptance

- Owner explicitly accepted aliases for all users.
- Rows appear after Germany in the exact order Poland, Netherlands, Finland,
  Sweden, with matching flags.
- Aliases are manual profiles only. They are excluded from AutoSelect, YouTube
  balancing and CDN fallback candidate sets.
- No Remnawave Host/inbound, port, firewall, DNS, certificate, node, quota,
  credential or subscription identifier changes.
- Plain/base64 and Happ JSON delivery both contain the four rows; real generated
  output contains the expected endpoints and ordering.

## Risk and rollback

- Users choosing an alias receive the underlying Germany or Estonia exit IP.
- Rollback is a subscription-code revert and subscription service restart; no
  server-side network cleanup is required.
