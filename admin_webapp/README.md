# ArcVPN Admin frontend

This directory contains a direct frontend source migration from
[`BEDOLAGA-DEV/bedolaga-cabinet`](https://github.com/BEDOLAGA-DEV/bedolaga-cabinet)
at commit `001531d04dda5c42f0b23b699e8408c6ca83ede9` (release 1.75.0).

The upstream React/TypeScript source, component system, layout and styling were
copied into this directory under the GNU Affero General Public License v3.0.
ArcVPN-specific changes are deliberately bounded to branding, routing,
read-only permission gates and API adapters in `src/arcvpn/` plus the documented
adapter points in `src/api/`.

The complete corresponding source for the deployed version must remain
available through the visible `Исходный код · AGPL-3.0` link in the interface.
See `LICENSE` and `NOTICE`.

## Local commands

```bash
npm ci
npm run type-check
npm run build
npm run dev -- --host 127.0.0.1
```

The development build uses deterministic fixture data. Production requests use
ArcVPN's existing `/api/admin/*` endpoints through `src/arcvpn/api.ts`.
