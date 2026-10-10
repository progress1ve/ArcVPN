# ArcVPN AI support and alert routing

Groq GPT-OSS 120B is the active target. The server uses a fixed allowlisted HTTPS endpoint, an 8-second timeout and two concurrent workers. Groq receives a low-reasoning request bounded to 1024 completion tokens, including its internal reasoning; reasoning is excluded from visible replies. Other supported providers are OpenAI Responses, OpenRouter and Gemini OpenAI-compatible API.

Only the last six redacted conversation texts are sent. Links, UUIDs, emails, common credential forms and phone numbers are masked. The model has no account tools, credentials or payment authority. Replies are visibly identified as the AI assistant. Payment/refund/person requests go to the manager; failures preserve that handoff. Late replies cannot overwrite a newer turn, human response or closed thread.

## Protected configuration

A root-only `/etc/arcvpn/support-ai.env` (0600) supplies `SUPPORT_AI_ENABLED`, `SUPPORT_AI_PROVIDER=groq`, `SUPPORT_AI_MODEL=openai/gpt-oss-120b`, `GROQ_API_KEY` and `SUPPORT_AI_ALERT_CHAT_ID`. The subscription service loads it through a systemd EnvironmentFile drop-in. Never store actual credentials in Git, browser code or logs. Disable the assistant with SUPPORT_AI_ENABLED=false and restart only the subscription service.

## Notification audience

The persisted setting `admin_notification_ids` stores the owners selected subset of configured ADMIN_IDS. Bot reports, fleet incidents, updates, maintenance, LTE monitoring and WebApp support notifications use this audience. ADMIN_IDS continues to authorize both administrators and show their admin menu/buttons. Unreadable selection fails closed. Explicit campaign test recipients and ordinary customer notifications are separate actions.

An inference failure sends the owner a sanitized notice without provider bodies or customer identifiers; repeated failure notices have a persisted six-hour cooldown. A later successful inference sends one recovery notice. Detection occurs when a support inference is attempted, not while the API is idle. Telegram delivery failure is retried on the next inference. Customer fallback is persisted before notification delivery.

## Provider comparison, checked 2026-10-10

| Provider | Conditions relevant to small support volume | Decision |
| --- | --- | --- |
| Groq | GPT-OSS 120B free-plan documentation lists 1000 requests/day, 30/minute, 200000 tokens/day, 8000/minute; actual key response confirms 1000/day and 8000/minute | Main provider with supplied key |
| OpenRouter | Free models: 50 requests/day, 20/minute; 1000/day after purchasing at least $10 credits | Possible replacement |
| Google AI Studio | Eligible Gemini free tiers; exact limits in the account dashboard; free-tier content may be used to improve products | Possible replacement after privacy/region review |

Free quotas and model availability may change. The owner accepts replacing the provider after an alert. There is no promised one-year SLA.

Sources: [Groq limits](https://console.groq.com/docs/rate-limits), [Groq models](https://console.groq.com/docs/models), [reasoning controls](https://console.groq.com/docs/reasoning), [OpenRouter limits](https://openrouter.zendesk.com/hc/en-us/articles/39501163636379-OpenRouter-Rate-Limits-What-You-Need-to-Know), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [Gemini limits](https://ai.google.dev/gemini-api/docs/rate-limits).
