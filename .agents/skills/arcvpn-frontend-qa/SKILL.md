---
name: arcvpn-frontend-qa
description: Plan, audit, build, and improve ArcVPN landing, customer WebApp, and admin UI with live browser inspection, responsive acceptance, interaction states, and visual evidence. Use for any ArcVPN frontend design, layout, responsiveness, accessibility, or interaction task.
---

# ArcVPN Frontend QA

1. Start from the requested outcome and surface mode: landing pages persuade,
   customer flows complete a task, and admin pages optimize rapid operation.
   Inspect the existing product, tokens, components, assets, and live page before
   proposing a visual direction. Code inspection alone is insufficient.
2. Before implementation, record the content hierarchy, primary conversion or
   task, required sections/states, reusable components, breakpoint behavior, and
   explicit exclusions. Resolve ambiguous public copy, pricing, URLs, and calls
   to action before mutation.
3. Capture concrete defects by page, component, viewport, severity, and reproduction.
4. Define acceptance in `.codex/stages/current.md`, including mobile, tablet, desktop, and wide layouts.
5. Check hierarchy, density, alignment, overflow, empty/loading/error states,
   keyboard focus, hover/active/disabled states, contrast, reduced motion, and
   copy readability. Reject generic AI patterns that conflict with ArcVPN's
   existing visual language, including unjustified glass cards, excessive
   rounding, decorative gradients, vague claims, and card-inside-card density.
6. Implement an original ArcVPN design using the project's existing Svelte stack
   and components. External products are behavior/reference inputs, not source to
   copy. Do not introduce React or shadcn/ui into the Svelte application merely
   to obtain a component that is simple to implement locally.
7. If Impeccable is already installed, use its design vocabulary and detector as
   an additional critique pass, while preserving ArcVPN tokens and this skill's
   acceptance gates. Its output is advice, not authority. Do not require the user
   to invoke it.
8. Run relevant automated checks, then inspect the deployed result at all four viewport classes.
9. Attach before/after evidence or precise screenshot paths to the stage artifact. A rendered page is not automatically accepted.
