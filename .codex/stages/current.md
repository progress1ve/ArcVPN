# Current stage — BEDOLAGA-inspired admin visual reset

## Goal

Replace the rejected ArcVPN admin visual layer with an original Svelte
implementation that follows the approved BEDOLAGA-like operational language:
flat near-black canvas, restrained dark surfaces, compact type, consistent
spacing, table-first information density and clear status accents.

## Non-goals

- No React/Tailwind migration and no BEDOLAGA source or component copying.
- No API, database, permission, payment or subscription behavior changes.
- No changes to public subscription URLs, UUIDs or customer access.

## Components

- `webapp/src/views/AdminConsole.svelte`: dashboard hierarchy and shared tokens.
- `webapp/src/components/admin/AdminNavigation.svelte`: restrained sidebar.
- `webapp/src/components/admin/AdminPageHeader.svelte`: compact page heading.
- `webapp/src/components/admin/AdminLogin.svelte`: matching auth surface.
- `webapp/src/views/admin/AdminUsers.svelte`: table-first users and Client 360.
- generated `webapp_dist` assets.

## Accepted visual contract

- Near-black flat background; no large decorative aurora in the workspace.
- Sidebar is quiet and compact; active item uses a subtle blue surface, not a
  bright filled pill or edge stripe.
- Page titles are 24–28 px; controls use 8/12/16/24 px rhythm.
- KPI cards are compact, use a small semantic icon tile and avoid nested cards.
- Nodes, operational queue and users read as dense lists/tables.
- Borders are thin, radii are mostly 10–16 px, shadows are minimal.
- Blue is reserved for selection/actions; green, amber and red mean status.
- Mobile keeps essential actions and uses a compact bottom navigation.

## Acceptance

- Shell, Overview and Users/Client 360 visibly share the new system.
- No old bright sidebar selection, giant headings, excessive glow, or oversized
  rounded dashboard cards remain in those surfaces.
- Existing loading, empty, error, stale, forbidden and permission states work.
- Routes and browser back/forward from the previous stage still work.
- No horizontal overflow at 390, 768, 1280 and 1600 px.
- Production build and browser review pass before deployment.

## Risks and rollback

- Dense tables can become unreadable below tablet width; mobile rows must
  deliberately collapse instead of shrinking every column.
- Legacy component-local CSS may override new tokens; verify computed output.
- Rollback by reverting the visual-reset commit and pulling it on production;
  static-only release requires no service restart.

## Verification matrix

- Local Svelte build and staged diff check.
- Browser: Overview and Users at 390/768/1280/1600.
- Browser: navigation, user drawer, keyboard focus and unauthorized login.
- Production: bundle asset requests, public login, service health.

## Local evidence

- Vite production build passed: 183 modules transformed.
- Desktop 1600 px: four compact KPI blocks, nodes and work queue above growth
  panels, flat sidebar state and no horizontal overflow.
- Users 1600 px: visible Client/Payments/Subscription/Traffic/Status columns;
  opening a row renders six facts, subscriptions, payments, timeline and actions.
- Users with the Client 360 drawer open passed 390, 768, 1280 and 1600 px
  overflow checks.
- Mobile 390x844 collapses table-only columns, keeps the identity/status row and
  exposes Client 360 as a readable two-column detail flow.
- Unauthorized 390 px view contains no sidebar, focuses the password input via
  keyboard navigation and has no horizontal overflow.
- Existing unused-selector warnings outside this stage remain non-blocking.
