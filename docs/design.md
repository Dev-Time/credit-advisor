# Credit Card Advisor — Design Document

Date: 2026-05-10
Status: Draft

---

## Overview

A Home Assistant-native credit card advisor platform that helps users decide which card to use for purchases, track benefit/credit usage, monitor annual value, and (eventually) discover and activate card offers. Starts as a personal tool with room for affiliate/referral monetization later.

**Roadmap phases:**
1. **MVP** — Query-based "which card for this purchase?" via Lovelace dashboard + HA conversation.
2. **Benefit tracking** — Dashboard + proactive notifications for monthly/quarterly/semiannual credits. Annual value tracking per card.
3. **Transaction hearing** — Android notification listener (via Tasker or custom app) for real-time transaction awareness.
4. **Offer scraping** — Headless browser (Nodriver/Camoufox) for offer discovery and auto-activation on home hardware.

---

## Architecture

Home Assistant provides the server, automation engine, push notifications, location zones, and dashboard. A custom HA integration (`credit_advisor`) provides the credit intelligence layer. **LLM calls are delegated to HA's built-in `ai_task.generate_data` service** (backed by OpenRouter) — no custom HTTP client or API keys needed in our component.

```
Lovelace Dashboard (input_text + markdown) ──┐
                                             │ call service
                                             ▼
  credit_advisor (custom_component/credit_advisor/)
    ├── config_flow.py      → one-step HA UI setup (no options needed)
    ├── __init__.py         → async_setup_entry, service definitions
    ├── const.py            → domain, service names, event types only
    ├── card_registry.py    → card CRUD, YAML I/O
    ├── benefit_tracker.py  → usage tracking, expiry calc, annual rollup
    ├── sensors.py          → benefit expiring, unused, annual value
    └── ───────────────────────────────────────
                        │
                        ▼
          ai_task.generate_data (HA built-in)
              │ routes through OpenRouter
              ▼
          OpenRouter API (configured in HA UI)
```

**No `configuration.yaml` block needed** — users add it via Settings → Devices & services → Add integration → Credit Card Advisor. The config flow creates the entry with no user-configurable options for MVP.

**Storage** (`[ha_config]/credit_advisor/`):
```
cards/            → YAML per card (amex_platinum.yaml, chase_sapphire.yaml)
benefits/         → usage YAML per benefit per year (uber_cash_2026.yaml)
history/          → optional query log (query_2026-05-10.yaml)
freshness.json    → last-refresh timestamp per card
```

---

## Card Data Model

```yaml
id: amex_gold
name: American Express Gold Card
issuer: American Express
annual_fee: 250
annual_fee_date: "2026-04-15"

benefits:
  - id: uber_cash
    name: Uber Cash
    type: monthly_credit
    amount: 10
    currency: USD
    frequency: monthly
    schedule: "first of month"
    valid_at: [Uber, Uber Eats]
    expires: end_of_month
    enrollment_required: false
    redemption: auto
    usage_history_path: benefits/uber_cash_2026.yaml

  - id: dining_credit
    name: Dining Credit
    type: monthly_credit
    amount: 10
    currency: USD
    frequency: monthly
    valid_at: [Grubhub, Goldbelly, Cheesecake Factory, etc.]
    expires: end_of_month
    enrollment_required: false
    redemption: auto

rewards:
  base:
    dining: 4x
    groceries_us: 4x
    flights: 3x (direct)
    transit: 1x
    everything_else: 1x
  special: []
```

---

## Benefit Usage Tracking (per period)

```yaml
# benefits/uber_cash_2026.yaml
benefit_id: uber_cash
card_id: amex_gold
year: 2026
periods:
  - period: "2026-01"
    used: 10.00
    remaining: 0.00
    status: fully_used
    last_used: "2026-01-08"
  - period: "2026-02"
    used: 4.50
    remaining: 5.50
    status: partially_used
    expires: "2026-02-28"
```

Annual value rollup: aggregates last 365 days from the card's annual fee date. Net value = sum of benefits used − annual fee.

---

## Query Interface (MVP)

**Via Lovelace dashboard (Option B):**
- `input_text.credit_query` — user types merchant + amount
- `input_button.credit_ask` — triggers automation
- Automation calls `credit_advisor.query` service with text
- Response written to `sensor.credit_response`
- Markdown card displays the response

**Prompt sent to LLM:**
Structured context with card YAML, purchase details, benefit balances. LLM returns: recommended card, alternatives, credits that could apply, warnings.

**Telegram also supported** via HA's Telegram integration calling the same service.

---

## Proactive Notifications

Custom sensors exposed by the integration:

| Sensor | Purpose |
|--------|---------|
| `sensor.credit_benefit_expiring` | Benefits ≤7 days from expiry |
| `sensor.credit_benefit_unused` | Benefits 50% through period with 0% usage |
| `sensor.credit_annual_value_{card_id}` | Net value of card since last AF date |
| `binary_sensor.credit_enrollment_needed` | Benefit requires enrollment, not enrolled |

User configures HA automations to trigger on these sensors and send push notifications via the HA mobile app.

---

## Annual Value Tracker

Per-card Lovelace display showing:
- Benefits used since last annual fee date (dollar total)
- Annual fee paid
- Net value (benefits − fee)
- % of maximum possible benefit value captured
- Benefit-by-benefit breakdown

Resets on each card's annual fee date, not calendar year.

---

## Auto-Refresh

Weekly automation calls `credit_advisor.refresh_benefits` which calls `ai_task.generate_data` with: "Has anything changed for this card's benefits?" Results in a notification if changes are detected; user reviews and confirms before updates are applied.

---

## Error Handling

1. **`ai_task` not configured** → prompt user to set up OpenRouter in HA UI (Settings → Devices & services → Add integration → OpenRouter)
2. **No cards stored** → prompt user to add cards via `credit_advisor.add_card`
3. **`ai_task` call fails** → log warning, return friendly message, never crash
4. **No `after_dependencies` met** → HA will delay loading our component until `ai_task` and `open_router` are available

---

## Future Phases (Not in MVP Scope)

- **Notification listener** (Tasker → HA webhook) for automatic transaction hearing
- **Transaction history import** (HA-YNAB integration, Plaid)
- **Offer scraping** (headless browser on home hardware, Tier 2)
- **Cloud automation** (TEE scraping, Tier 3)
- **Affiliate/referral monetization** (long-term, delayed entry)
- **Custom Lovelace chat card** (replaces Option B, adds chat history)
- **Structured rules engine** (replaces LLM for deterministic benefit matching)

---

## Testing

| Area | Approach |
|------|----------|
| Card data accuracy | Manual review after LLM-assisted entry |
| Query results | Daily spot-check, log disagreements |
| Benefit math | Unit test: period aggregation, annual rollup |
| Notification triggers | Simulate sensor state in dev, verify automations |
| LLM consistency | Log prompt+response pairs, periodic audit |
