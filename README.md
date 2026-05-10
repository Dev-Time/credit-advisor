# Credit Card Advisor

A privacy-first credit card advisor platform that runs inside Home Assistant. Helps you decide which card to use for purchases, tracks benefit usage, and maximizes the value of premium card credits.

## Philosophy

Built for personal use first. Privacy-as-a-feature — all card metadata and benefit tracking lives on your hardware. LLM-assisted entry and recommendations, with your financial data never leaving your control.

## Roadmap

| Phase | Status | What |
|-------|--------|------|
| **1. Query Engine** | 🔜 Planned | Ask "which card for this purchase?" via Lovelace dashboard. LLM-powered recommendation using locally stored card data. |
| **2. Benefit Tracking** | 📋 Next | Dashboard showing monthly/quarterly credit usage, expiry alerts, annual value tracking per card. |
| **3. Transaction Hearing** | 🔮 Future | Android notification listener (Tasker) for real-time transaction awareness. |
| **4. Offer Scraping** | 🔮 Future | Headless browser for offer discovery and auto-activation. |

## Architecture

Home Assistant custom component (`custom_components/credit_advisor/`) with:

- **Card Registry** — YAML-based local storage for card definitions
- **LLM Client** — OpenRouter-powered recommendation engine
- **Sensors** — Benefit expiry, usage, and annual value state tracking
- **Lovelace Dashboard** — Native HA cards (input_text + markdown) for the query interface

## Usage (MVP)

1. Add your cards via `credit_advisor.add_card` service
2. Open the Credit Advisor Lovelace view
3. Type e.g. "Chipotle $14" and press "Ask the Advisor"
4. Get a recommendation with reasoning

## Design

See [`docs/design.md`](docs/design.md) for the full architecture spec.
See [`docs/plan.md`](docs/plan.md) for the MVP implementation plan.