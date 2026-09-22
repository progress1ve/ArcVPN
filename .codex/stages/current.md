# User feedback in Admin and trial win-back — 2026-09-22

## Goal

Return lifecycle questionnaire answers in the existing protected user-detail API
and show them in a compact dedicated «Ответы» tab in Client 360. Prepare, but do
not send or enable, a segmented trial-to-paid win-back offer.

## Visible contract

| Surface | Required behavior |
| --- | --- |
| User API | `/api/admin/users/<id>` returns only that user's answered lifecycle records with event key, answer and timestamps. |
| User card | «Ответы» shows the question, a readable Russian answer, optional free-text detail and answer time. |
| Empty state | Users without answers get a clear compact empty state, not a blank or an error. |
| Access | Existing `users:overview` permission remains the only read gate; no private subscription values are added. |
| Campaign | No discount, promocode or broadcast is created or sent in this stage. |

## Components

- Backend: `subscription_api.py` user-detail response.
- Frontend: `admin_webapp/src/api/adminUsers.ts`, user-detail page and a new
  answers tab component.
- Verification: focused backend/frontend tests, TypeScript and production
  build. Browser QA is explicitly delegated to the owner for this release.

## Acceptance

- Trial rating and expired win-back answers map to readable Russian text.
- Free-form detail after an answer code remains visible.
- Records from a different user never appear in the response.
- Existing databases without the optional lifecycle table return an empty list.
- Focused tests, TypeScript and production build pass.
- If released, production pulls with `--ff-only`, only the subscription service
  is restarted, the service is active, and HTTP/API smoke checks pass.

## Risks and rollback

- Read-only query only; it does not alter lifecycle answers or bot behavior.
- Unknown future answer codes fall back to the stored value rather than vanish.
- Rollback is a Git revert, admin rebuild and subscription-service restart.
