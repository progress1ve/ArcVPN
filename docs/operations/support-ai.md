# ArcVPN AI support

The optional assistant uses OpenAI Responses with `gpt-4.1-mini`, an 8-second
provider timeout, 350 output tokens and at most two concurrent workers. Existing
user message limits, authentication and manager notifications remain in force.
Each reply is labeled **ИИ-помощник ArcVPN**, including in the admin conversation.
Payments, refunds and requests for a person receive a manager handoff. Provider
failure preserves that handoff. A late reply cannot overwrite a newer user turn,
a human reply or a closed thread.

Only the last six conversation texts are sent. Subscription URLs, VPN links,
emails, common credential forms, UUIDs and phone numbers are redacted; no account
identifiers, subscription data or service credentials are included. OpenAI
response storage is disabled. The assistant has no tools or account-write access.

## Activation

The release is **disabled until a separate API credential is configured**.
A ChatGPT/Codex subscription does not create the service's API key or fund its
API billing. Create a dedicated restricted project key in the OpenAI dashboard
and configure its spending controls. Do not put keys in Git, browser code, chat
messages or logs.

Install these values through a root-only service environment file and a systemd
`EnvironmentFile` drop-in for `arcvpn-subscription.service`:

```text
SUPPORT_AI_ENABLED=true
OPENAI_API_KEY=<secret from the dedicated project>
SUPPORT_AI_MODEL=gpt-4.1-mini
```

After configuration, restart only the subscription service and verify one
non-sensitive support question with a dedicated test account: pending indicator,
labeled real response, latency, manager notification and no duplicated reply.
Until that check passes, do not claim production AI inference is verified.
Disable immediately by setting `SUPPORT_AI_ENABLED=false` and restarting the same
service. No database migration or deletion is required: AI replies use existing
`admin` rows with reserved sender ID `0`, serialized with `is_ai=true`.

Sources: [model](https://developers.openai.com/api/docs/models/gpt-4.1-mini),
[text generation](https://developers.openai.com/api/docs/guides/text),
[subscription/API pricing distinction](https://learn.chatgpt.com/docs/pricing).
