# Stage: Public ArcVPN landing — art-direction correction

## Goal

Replace the rejected card-heavy landing treatment with a restrained cinematic
product narrative while preserving the current cabinet, authentication,
payment, import, admin and subscription contracts.

## Non-goals

- Do not reproduce Happ or INCY as a fake interactive client.
- Do not expose protocols, hosts, ports, UUIDs, topology or live node state.
- Do not fabricate social links, prices, ping values or product screenshots.
- Do not copy the attached Aura prompt's React/Tailwind implementation or its
  product copy; use it only for hierarchy, restraint and realistic product proof.
- Do not modify the owner's `Connect.svelte` edit or deleted landing prompt.

## Components

- Public `/` landing and isolated frontend chunk, substantially re-typeset and
  re-arranged using an Impeccable critique/distill pass.
- Existing `/app` cabinet with stable landing-intent query parameters.
- Safe public tariff, catalog, custom quote and public-link endpoints.
- Stable Hero backdrop with no simulated camera movement or visible loop seam.
- Realistic client and cabinet device stages with clearly marked screenshot
  placeholders until owner-supplied proof is available.
- Metadata, sitemap, no-JavaScript fallback and analytics adapter.

## Acceptance

- Product precedes price and all approved content remains, but related sections
  are consolidated into a few deliberate scenes instead of repeated cards.
- Hero reads like one cinematic frame, not a centered SaaS template.
- Subscription proof resembles the information density of a real desktop VPN
  client while omitting protocol, host, port, UUID and fabricated ping.
- The custom tariff always shows the server-calculated price; on local preview a
  transparent preview label is allowed, but production never invents a price.
- Cabinet proof uses laptop/phone frames and explicit screenshot placeholders.
- Mobile 360/390, tablet 768 and desktop 1280/1920 have no overflow or overlap.
- Navigation, menu, demos, pricing, calculator and FAQ are keyboard accessible.
- Prices and the profile list come from server contracts; local errors stay local.
- Landing, cabinet and admin-heavy code remain separate build chunks.
- `/app` authentication and product/period/connect/custom intent still work.

## Release decision

- The owner explicitly requested production publication on 2026-09-07.
- Screenshot placeholders are accepted for this release and remain clearly
  labelled; exact Instagram/TikTok links remain hidden until provided.
- Runtime commits `89b1595` and `d6c9613` are deployed on `pl-control`.

## Risks and rollback

- Rollback the landing runtime commit to restore the old root shell; `/app` and
  public subscription URLs remain stable.
- Keep public responses allowlisted, short-cached and content-ETag validated.

## Design direction

- Color: ink `#030508`, carbon `#0A0D12`, snow `#F4F7FA`, steel `#8D98A7`,
  current `#66BFFF`, deep current `#06274A`.
- Type: Manrope only; editorial left-aligned display, compact product UI, no
  uppercase eyebrow repeated above every heading.
- Layout: cinematic hero → one desktop client stage crossing the fold → short
  feature rail → pricing → custom quote → laptop/phone cabinet proof → steps/FAQ.
- Principle: spend visual boldness on the blue current and product frames; keep
  every other surface flat, sparse and aligned to one 1180 px grid.

## Verification

Previous draft evidence is retained only as before-state. Final evidence:

- `pytest -q`: 177 passed; Vite production build passed.
- Impeccable detector: exit 0 with no findings.
- Production browser at 390x844, 768x1024, 1280x800 and 1600x900: no overflow,
  no video, no landing console errors; mobile menu and interactive price/profile
  states passed.
- Production `/`, `/app`, all four public endpoints, sitemap and Hero asset:
  HTTP 200. Service is active and the production revision is `d6c9613`.
