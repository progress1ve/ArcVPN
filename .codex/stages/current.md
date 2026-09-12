# Current stage — Admin Platform foundation

## Goal

Ship the first independently releasable slice of the approved Admin roadmap:
a route-based, permission-aware Svelte shell with a standalone authentication
surface, grouped navigation and denser operational layout. Existing business
behavior and API contracts remain unchanged.

## Non-goals

- No payment mutations, ticket workflow, node writes or database migration.
- No React migration and no source/component copying from BEDOLAGA.
- No changes to subscription URLs, user UUIDs or active-user access.

## Components

- `webapp/src/views/AdminConsole.svelte`
- `webapp/src/components/admin/AdminLogin.svelte`
- `webapp/src/components/admin/AdminNavigation.svelte`
- `webapp/src/components/admin/AdminPageHeader.svelte`

## Contract

- `/admin` opens Overview; `/admin/<section>` deep-links to an allowed section.
- Browser back/forward changes the active section without a reload.
- Unknown or forbidden sections fall back to the first permitted destination.
- Navigation groups are Operations, Clients, Finance, Infrastructure, Growth,
  and System; groups containing no allowed pages are hidden.
- Until access is established, sidebar and operational header are not rendered.
- Login preserves existing password and Telegram session behavior.
- Existing permission checks and every current section remain available.

## Acceptance

- Existing sections render through the new shell without API/business changes.
- Active route, browser history and permission fallback work in a real browser.
- Login is a standalone centered surface with no leaked workspace chrome.
- Layout passes 390, 768, 1280 and 1600 px review with no horizontal overflow.
- Loading, authentication, forbidden and stale-refresh states remain explicit.
- `npm run build` passes and generated `webapp_dist` is reviewed in the diff.

## Risks and rollback

- Deep links can select a page before permissions load; resolve only after access
  is known and replace invalid history entries.
- Telegram auth query parameters must survive route navigation.
- Rollback is a single stage commit plus rebuild of committed static assets.

## Verification plan

- Build the Svelte application.
- Inspect diff and generated asset references.
- Exercise direct navigation, click navigation and browser back/forward.
- Capture browser evidence at all four target widths, including unauthenticated
  layout where locally reproducible.

## Evidence

- Production Svelte build passes (183 modules transformed).
- Direct navigation to `/admin/users`, click navigation, and browser back to
  `/admin` were verified in the in-app browser.
- Unknown `/admin/not-a-section?source=qa` is replaced with
  `/admin?source=qa`; the query string is preserved.
- A support-only role requesting `/admin/users` is routed to `/admin/support`
  and receives no Users navigation item.
- Width checks at 390, 768, 1280 and 1600 px report no horizontal overflow.
- Unauthorized mobile state at 390 px renders `Вход в Admin` without the
  sidebar and without horizontal overflow.
- Existing Svelte unused-selector warnings remain non-blocking; the new login
  autofocus warning was removed.
