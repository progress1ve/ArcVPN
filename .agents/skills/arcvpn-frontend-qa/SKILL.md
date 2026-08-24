---
name: arcvpn-frontend-qa
description: Audit and improve ArcVPN admin UI with live browser inspection, responsive acceptance, interaction states, and visual evidence. Use for any admin-panel design, layout, responsiveness, accessibility, or interaction task.
---

# ArcVPN Frontend QA

1. Use the in-app browser to inspect the live page before editing. Code inspection alone is insufficient.
2. Capture concrete defects by page, component, viewport, severity, and reproduction.
3. Define acceptance in `.codex/stages/current.md`, including mobile, tablet, desktop, and wide layouts.
4. Check hierarchy, density, alignment, overflow, empty/loading/error states, keyboard focus, hover/active/disabled states, and contrast.
5. Implement an original ArcVPN design. External products are behavior/reference inputs, not source to copy.
6. Run relevant automated checks, then inspect the deployed result at all four viewport classes.
7. Attach before/after evidence or precise screenshot paths to the stage artifact. A rendered page is not automatically accepted.
