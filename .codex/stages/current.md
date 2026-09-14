# Admin readability and layout correction — 2026-09-14

## Goal and evidence
Owner rejected the deployed design: 8–11 px text, low-contrast captions,
unlabelled traffic values and excessive horizontal separation on 2560 px screens.
The two owner screenshots are the before evidence.

## Contract
- Body and table values 14 px; secondary text at least 12 px.
- Foreground #eaf0f8, secondary #a6b4c8 on #131c2b surfaces.
- System UI font with normal 400/500/600 weights and tabular numeric values.
- Overview presents KPIs, network and operator queue before growth detail.
- Nodes are full-width rows with explicit status and online labels.
- Users have labelled main/LTE values and real readable filters.
- Primary content remains at most 1480 px wide, aligned inside a 248 px shell.
- Existing APIs, business operations and permission behavior are preserved.

## Components
AdminConsole, AdminUsers, AdminNavigation and AdminPageHeader.
Replace conflicting local style layers where mapped; no unrelated owner files.

## Acceptance
Build passes; screenshots and DOM checked at 390, 768, 1280, 1600 and 2560.
Check internal container overflow as well as document overflow.
Verify user detail and navigation; preview uses synthetic data, production login
is checked separately. Typography and contrast must be measured, not inferred.

## Verification evidence
- `npm run build`: passed; 183 modules transformed.
- Users and overview: no document or internal-container overflow at 390, 768,
  1280, 1600 and 2560 px.
- Users: table values 14 px, names 15 px and secondary text 12 px.
- Secondary text contrast measured at 8.13:1 on the table surface.
- Client 360, navigation, empty state and recoverable error state verified in browser.
- Owner requested production release while explicitly noting that the broader
  visual direction still needs another design iteration; this release therefore
  closes the readability correction, not final aesthetic approval.

## Rollback
Revert this stage commit; frontend-only assets do not require service restart.
