# Admin reliability, branding and monthly profit — 2026-09-22

## Goal

Make the admin first render deterministic and Russian, show real active-trial
counts, use the owner-provided ArcVPN mark as a native SVG, and keep every
admin route dark without offering a light-theme toggle. Add an operator-facing
monthly profit report with accrual revenue and editable operating expenses.

## Visible contract

| Surface | Required behavior |
| --- | --- |
| First render | Admin navigation never renders raw keys such as `admin.groups.analytics`; the Russian fallback bundle is ready before React mounts. |
| Brand | Desktop and mobile admin headers show the white ArcVPN vector mark matching `arcLOGO_NEW22.webp`, not the fallback `A`. |
| Trial statistic | `Триалы` equals distinct users with `trial_entitlements.status='active'` whose linked key is not expired. Paid/completed trials are excluded. |
| Theme | Every `/admin` route starts and remains dark. Desktop/mobile theme buttons are absent on admin routes. Customer routes retain their existing theme behavior. |
| Profit | `/admin/profit` allocates each successful paid subscription across its paid months, excludes trials, subtracts one-time and recurring expenses, and exposes a 12-month comparison. |
| Expenses | Owner/finance roles can add categorized hosting, CDN, advertising or other expenses and remove them with a confirmation step and audit event. |

## Components

- Startup/localization: `admin_webapp/src/main.tsx`, i18n regression tests.
- Brand: new native SVG component plus desktop/mobile admin header consumers.
- Theme: `index.html`, `useTheme`, desktop and mobile header controls.
- Data: `database/db_statistics.py`, ArcVPN dashboard adapter and focused tests.
- Profit: existing `service_expenses`, enhanced `/api/admin/expenses`, new
  `AdminProfit` route, navigation entry, monthly chart and calculation tests.

## Acceptance

- Cold-cache test proves React mounts only after `i18nReady` and translated Russian labels render.
- Dashboard/backend tests prove non-zero active trial counts and exclude completed trials.
- Browser evidence shows the SVG mark, Russian labels, non-zero trials, dark styling and no theme toggle.
- TypeScript, focused Vitest, full Python tests and production build pass.
- A 400 ₽ four-month payment contributes exactly 100 ₽ to each covered month; recurring and one-time expenses apply to the correct months.
- Production service remains active; public admin HTML and bundle return 200.

## Risks and rollback

- Locale readiness retains its bounded timeout.
- Trial stats add one indexed aggregate to overview.
- Theme forcing is scoped to `/admin`.
- Rollback is a Git revert, admin rebuild and subscription-service restart.

## Release evidence

- Commit: `3ac044c`; pushed to `main` and pulled with `--ff-only` on `pl-control`.
- Backend: 210 tests passed; focused profit/trial checks passed after final rebase.
- Frontend: type-check, production build and 10 focused i18n/dashboard tests passed.
- Browser: mobile admin and profit route verified locally; production login is
  dark, Russian and shows the SVG logo.
- Production: service active, overview reports trial 3 / paid 14, admin HTML and
  new bundle return 200, unauthenticated expenses request returns 403.
- Rollback: revert `3ac044c`, pull and restart only `arcvpn-subscription.service`.
