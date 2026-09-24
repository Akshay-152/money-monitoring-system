# FLUX Money OS

FLUX is an offline-friendly personal finance tracker for Indian users. It stores a local ledger in SQLite, formats money as INR, suggests categories for UPI merchants, and exposes a Flask REST/SSE API with a zero-build vanilla JavaScript frontend.

## Quickstart

### Docker (recommended)

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:5000. The app is usable immediately: add manual entries, classify pending entries, create goals, and search the ledger. Data persists in the `flux-data` Docker volume.

### Without Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m backend.api.app
```

Run tests with `pytest -q`. No Gmail, Redis, LLM, or cloud account is required for the default app and test suite.

## What is implemented

- SQLite `StorageBackend` with transactions, soft deletion, budgets, goals, summaries, and parameterized SQL.
- Bank-alert parser for common debit/credit formats, merchant normalization, keyword categorization, and a guarded LLM extension point.
- REST endpoints from the contract, validation with Pydantic, CORS configuration, health endpoint, and SSE heartbeat/events.
- Responsive dark/light FLUX interface with INR formatting, manual entry, search, pending categorization, budgets, goals, and theme persistence.
- Docker Compose, `.env.example`, GCP Pub/Sub setup script, and isolated Gmail integration boundaries.

The default webhook intentionally accepts no Gmail message data. Real Gmail ingestion needs OAuth credentials and OIDC verification before it should be enabled in production.

## Key configuration and how to get it

Copy `.env.example` to `.env` first. The local defaults are enough to start.

| Variable | Required for | Where to get it |
| --- | --- | --- |
| `DATABASE_PATH` | SQLite location | Keep `data/flux.db` locally or use the Docker volume path |
| `FRONTEND_ORIGIN` | Browser/API CORS | Your deployed frontend URL; use `*` only for local development |
| `REDIS_URL` | Redis-backed worker deployment | Your Redis URL; local Compose uses `redis://redis:6379/0` |
| `GOOGLE_PROJECT_ID` | Gmail/Pub/Sub | Google Cloud Console, project selector |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Gmail OAuth | Google Cloud Console > APIs & Services > Credentials > OAuth client |
| `PUBSUB_AUDIENCE` | Verified Pub/Sub push endpoint | The public HTTPS URL ending in `/gmail/webhook` |
| `PUBSUB_SERVICE_ACCOUNT` | Authenticated push delivery | A Google service-account email created in IAM |
| `LLM_API_KEY` | Optional parser fallback | Provider dashboard; leave blank by default because email contains PII |

### Gmail and Pub/Sub setup

1. Create/select a Google Cloud project and enable Gmail API and Pub/Sub API.
2. Configure the OAuth consent screen and add `https://www.googleapis.com/auth/gmail.readonly`. Google verification is required for public apps; Testing mode supports up to 100 test users.
3. Create an OAuth web client and put its client ID/secret in `.env`. Add the app URL to authorized origins and redirect URIs.
4. Deploy the API behind a public HTTPS URL, set `PUBSUB_AUDIENCE` to that URL, and create a service account for authenticated Pub/Sub pushes.
5. Run `GOOGLE_PROJECT_ID=... PUBSUB_AUDIENCE=... PUBSUB_SERVICE_ACCOUNT=... bash gcp/setup.sh`.
6. Complete OAuth for the Gmail user, then implement/register `GmailClient.watch()` for that user. The watch must be renewed before its seven-day expiry.

Never commit `.env`, OAuth tokens, service-account JSON, or raw email bodies. Pub/Sub push verification must validate the OIDC token audience with Google's auth library before processing a notification.

## Architecture

```text
Browser (frontend/) --> Flask API (backend/api/) --> StorageBackend --> SQLite
                              |\
                              | +--> SSE stream --> browser
                              +--> parser/categoriser --> transaction ledger
Gmail --> Pub/Sub OIDC webhook --> Gmail adapter --> parser --> Redis/message bus
```

The parser does not import the API or Gmail modules. Storage and messaging are abstracted so Postgres, Firestore, Redis, or another notifier can be added without changing route logic.

## API examples

```bash
curl http://localhost:5000/health
curl -X POST http://localhost:5000/api/transactions \
  -H 'Content-Type: application/json' \
  -d '{"amount":-50,"description":"Lunch","category":"Food","payment_mode":"UPI"}'
curl 'http://localhost:5000/api/transactions?month=2026-09&q=lunch'
```

## Adding a bank parser

Add a bank-specific regex and fixture under `backend/parsing/regex_patterns.py` and `tests/fixtures/emails/`, then add a focused test in `tests/test_parser.py`. Keep the returned fields aligned with the normalized transaction model: amount, direction, merchant, date, bank, and email message ID.

## Swapping storage

Implement `StorageBackend` in `backend/core/storage.py`, then update `create_storage()` to select it from `STORAGE_BACKEND`. Keep route code dependent on the abstract contract, not SQL or provider SDKs.

## Next steps

1. Add the real Gmail OAuth callback and encrypted token storage.
2. Replace the webhook stub with Google OIDC token verification and Gmail history cursor handling.
3. Add Redis persistence for history IDs, seven-day message deduplication, and a parser worker.
4. Add Postgres/Firestore adapters and authenticated multi-user tenant IDs before public deployment.
5. Add 15+ bank fixtures and an integration test for webhook -> parser -> SSE using `InMemoryBus`.
6. Configure HTTPS, backups, rate limiting, structured logging, and monitoring for production.


Master Prompt: Build FLUX Money OS — AI-Powered Personal Finance Tracker with Gmail UPI Integration

Below is a complete, copy-paste-ready prompt you can feed to an AI coding assistant (Claude Code, Cursor, Windsurf, etc.) or use as a technical specification document for a human developer. It is deliberately structured so the AI produces a working, extensible application in one shot.

---

THE PROMPT

---

ROLE

You are a senior full-stack engineer building a production-grade personal finance tracker for Indian users. You write clean, modular, testable code. You prioritise extensibility over cleverness — every module must be replaceable without touching the rest of the app. You document assumptions inline and never hardcode secrets.

---

PRODUCT VISION

Build FLUX Money OS — a minimal, fast, offline-capable web application that:

1. Automatically detects UPI payments by reading bank alert emails from the user's Gmail inbox (via Gmail API + Google Cloud Pub/Sub push notifications — no polling).
2. Prompts the user to categorise each detected payment the next time they open the app ("You paid ₹50 — what was this for?" with tappable category chips).
3. Stores categorised transactions in a database, computes running balance, and displays insights via charts.
4. Formats all money in Indian Rupees (₹) using en-IN locale (lakh/crore grouping: ₹1,23,456.78).
5. Runs entirely in Docker Compose so a developer can docker compose up and have the full stack working in under 2 minutes.
6. Is designed for extension — the parser, storage backend, auth provider, and notification channels must all be swappable via configuration.

The target user is an individual (not a business) who wants zero-friction expense tracking without manually entering every UPI payment.

---

CORE FUNCTIONAL REQUIREMENTS

F1. Gmail Ingestion Pipeline

· Register a Gmail users.watch() on the user's INBOX with a Pub/Sub topic.
· Receive Pub/Sub push notifications at POST /gmail/webhook (verified via OIDC bearer token).
· On notification, call history.list since the last processed historyId, fetch each new message via messages.get, and hand off to the parser.
· Renew the watch automatically every 6 days (watch expires at 7 days). Run this in a background thread or a scheduled task.
· Store the last processed historyId in Redis (or Postgres) so restarts don't lose position.

F2. UPI Email Parser

· Support at minimum these banks: HDFC, ICICI, SBI, Axis, Kotak, Yes Bank, IDFC First, Punjab National Bank.
· Extract: amount (float), merchant (string), direction ("debit" | "credit"), timestamp, bank, raw_email_id.
· Use a layered parsing strategy:
  1. Layer 1 — Regex: bank-specific patterns matching Rs. 450.00 debited ... UPI/xxxxx-MERCHANT style strings. Fast, deterministic.
    2. Layer 2 — Fallback LLM: if regex fails, send the email body to an LLM (Anthropic Claude or OpenAI, configurable) with a strict JSON-output prompt to extract the same fields. Log every LLM fallback so patterns can be added later.
      3. Layer 3 — Manual flag: if both fail, mark transaction as parse_failed: true and surface it to the user as "We couldn't read this payment — please enter details manually."
      · Normalise merchant names: uppercase, strip trailing numbers, strip @upi, strip -PAYMENT, map VPA handles to readable names where known.

      F3. Auto-Categorisation

      · Maintain a keyword → category map (see appendix below) covering common Indian merchants.
      · On parse, assign a suggested_category. Do not auto-mark as classified — user must confirm.
      · Learn: if the user changes a suggested category for a known merchant 3 times, persist the correction so future transactions from that merchant default to the corrected category.
      · Store the learning map in the database, not in code.

      F4. Categorisation Prompt (UI)

      · On every page load (and on every SSE event during a session), fetch unclassified transactions.
      · If any exist, show a bottom-sheet modal (mobile) / centered card (desktop) with:
        · Amount in large text (₹50 or ₹-50)
          · Merchant name (or "Unknown UPI payment")
            · Date
              · A grid of category chips: Rent, Groceries, Food, Transport, Shopping, Bills, Entertainment, Health, Education, Travel, Investment, Gift, Other
                · A "Skip for now" text button
                · On tap of a chip: POST /api/classify, close the modal, show a toast "Saved as Groceries".
                · If multiple unclassified transactions exist, queue them and show them one at a time.

                F5. Manual Entry

                · Form to add a transaction manually (amount, date, description, category, payment mode: UPI / Cash / Debit Card / Credit Card / Net Banking / Wallet / Auto Debit).
                · This must work even if Gmail is not connected (offline-first fallback).

                F6. Transactions & History

                · List transactions grouped by date (Today / Yesterday / date).
                · Filter by month, search by description/merchant/category.
                · Show per-day totals.
                · Delete a transaction (soft delete — keep in DB with deleted_at).

                F7. Budgets

                · User can set a monthly budget per expense category.
                · Dashboard shows a progress bar per budgeted category: ₹spent / ₹limit with colour coding (green < 80%, yellow 80–100%, red > 100%).
                · Show "over by ₹X" or "₹Y left".

                F8. Savings Goals

                · User creates goals with name, target amount, current saved amount, emoji icon.
                · Progress bar per goal.
                · "Add funds" button that opens an inline input for a contribution amount.
                · Goals are independent of the transaction ledger (contributions don't appear as transactions — this keeps it simple).

                F9. Charts

                · 6-month flow: stacked or grouped bars showing income vs expense per month.
                · Category doughnut: this month's spending broken down by category.
                · Running balance line: cumulative balance over time.
                · Use Chart.js. All chart colours must read from CSS custom properties so they update on theme change.

                F10. Theming

                · Two themes: dark (default) and light.
                · User's choice persists in localStorage.
                · Respect prefers-color-scheme on first visit.
                · All colours defined as CSS custom properties on :root[data-theme="dark"] and :root[data-theme="light"]. No hardcoded colours anywhere else.
                · Include a sun/moon toggle button in the header.

                F11. Responsiveness

                · Mobile-first. Test at 320px, 375px, 768px, 1280px.
                · Tab bar collapses gracefully on narrow screens.
                · Charts resize on window resize (debounced 200ms).
                · Use env(safe-area-inset-bottom) for iOS notch.
                · Touch targets ≥ 44×44px.

                ---

                TECHNICAL ARCHITECTURE

                Stack

                Layer Technology Notes
                Frontend Plain HTML5, CSS3, vanilla JS (ES2020+) No framework. Must be readable by a beginner.
                Charts Chart.js 4.x Loaded from CDN.
                Icons Font Awesome 6.x CDN.
                Fonts DM Sans + Space Mono Google Fonts.
                Backend API Python 3.11 + Flask REST + Server-Sent Events.
                Parser worker Python 3.11 Standalone process, subscribes to Redis.
                Gmail webhook Python 3.11 + Flask Separate small service.
                Messaging Redis 7 (Pub/Sub) Channels: flux:gmail_notifications, flux:transactions.
                Database Pluggable — default SQLite, optional Postgres, optional Firestore Behind a StorageBackend interface.
                Auth Pluggable — default "single-user, no auth"; optional Firebase Auth Behind an AuthProvider interface.
                Containerisation Docker + Docker Compose Multi-stage builds.
                Reverse proxy nginx (frontend container) Serves static files + proxies /api to Flask.

                Module Boundaries (must be respected)

                ```
                backend/
                ├── core/
                │   ├── storage.py        # StorageBackend ABC + SQLiteStorage, PostgresStorage, FirestoreStorage
                │   ├── auth.py           # AuthProvider ABC + NoAuthProvider, FirebaseAuthProvider
                │   ├── messaging.py      # RedisBus + InMemoryBus (for testing)
                │   └── money.py          # All ₹ formatting, parsing, rounding utilities
                ├── gmail/
                │   ├── client.py         # GmailClient (watch, history, get_message)
                │   ├── webhook.py        # Pub/Sub push receiver
                │   └── watch_renewer.py  # Background thread
                ├── parsing/
                │   ├── regex_patterns.py # Bank-specific patterns
                │   ├── llm_fallback.py   # LLM-based parser
                │   ├── normaliser.py     # Merchant name cleanup
                │   └── categoriser.py    # Keyword → category, plus learning
                ├── workers/
                │   └── parser_worker.py  # Redis subscriber
                ├── api/
                │   ├── app.py            # Flask app factory
                │   ├── routes/
                │   │   ├── transactions.py
                │   │   ├── budgets.py
                │   │   ├── goals.py
                │   │   └── stream.py     # SSE endpoint
                │   └── schemas.py        # Pydantic/dataclass models for request/response
                └── config.py             # Env-driven settings
                ```

                Rule: The parsing/ module must never import from api/ or gmail/. The gmail/ module must never import from api/. This keeps the core logic reusable for future CLI tools or mobile clients.

                Data Model

                ```python
                # Transaction
                {
                  "id": "uuid",
                    "amount": -50.0,              # negative = debit, positive = credit
                      "currency": "INR",             # always INR for now, but stored for future
                        "merchant": "GROCERY_STORE",
                          "merchant_raw": "UPI/412839-GROCERY_STORE@ybl",
                            "category": "Groceries",       # empty string until user classifies
                              "classified": False,
                                "payment_mode": "UPI",         # UPI | Cash | Debit Card | Credit Card | Net Banking | Wallet | Auto Debit
                                  "source": "gmail",             # gmail | manual | import
                                    "bank": "hdfc",
                                      "email_message_id": "...",     # for dedup
                                        "date": "2025-04-15",
                                          "ts": 1744718400000,
                                            "deleted_at": None,
                                              "parse_failed": False,
                                                "notes": ""
                                                }

                                                # Budget
                                                { "category": "Food", "monthly_limit": 5000 }

                                                # Goal
                                                { "id": "uuid", "name": "New Laptop", "target": 80000, "saved": 12000, "emoji": "💻" }

                                                # MerchantRule (learning)
                                                { "merchant_key": "GROCERY_STORE", "category": "Groceries", "confirmations": 3 }
                                                ```

                                                ---

                                                API CONTRACT

                                                All endpoints return JSON. Errors use { "error": "message", "code": "ERROR_CODE" }.

                                                Method Path Purpose
                                                GET /api/transactions?month=2025-04&q=search List (with filters)
                                                POST /api/transactions Manual add
                                                DELETE /api/transactions/:id Soft delete
                                                POST /api/classify { id, category } — classify a transaction
                                                GET /api/budgets Get all budgets
                                                PUT /api/budgets/:category { monthly_limit }
                                                GET /api/goals List goals
                                                POST /api/goals Create goal
                                                PATCH /api/goals/:id Update saved amount
                                                DELETE /api/goals/:id Delete goal
                                                GET /api/summary?month=2025-04 Aggregates for dashboard
                                                GET /api/stream SSE — pushes new parsed transactions in real time
                                                POST /gmail/webhook Pub/Sub push receiver (separate service)
                                                GET /health Liveness probe

                                                SSE contract: /api/stream emits events of shape { type: "transaction" | "classified" | "heartbeat", data: {...} }. Send a heartbeat every 25 seconds so proxies don't kill the connection.

                                                ---

                                                GMAIL INTEGRATION — DETAILED SPEC

                                                Pub/Sub Setup (documented in gcp/setup.sh)

                                                ```bash
                                                gcloud pubsub topics create gmail-notifications
                                                gcloud pubsub subscriptions create gmail-push \
                                                  --topic=gmail-notifications \
                                                    --push-endpoint=${PUBSUB_AUDIENCE}/gmail/webhook \
                                                      --push-auth-service-account=${SA_EMAIL}
                                                      gcloud pubsub topics add-iam-policy-binding gmail-notifications \
                                                        --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
                                                          --role="roles/pubsub.publisher"
                                                          ```

                                                          OAuth Scopes

                                                          · https://www.googleapis.com/auth/gmail.readonly — required to read bank alert emails.
                                                          · Document clearly in the README: this scope requires Google verification for public apps, but works in "Testing" mode with up to 100 test users with no verification.

                                                          Watch Lifecycle

                                                          · Register on app startup.
                                                          · Persist expiration timestamp to storage.
                                                          · Background thread checks every 6 hours: if expiration - now < 24h, renew.
                                                          · Handle watch failures gracefully — log, retry with exponential backoff, and surface a warning in the UI ("Gmail sync paused — reconnect").

                                                          Deduplication

                                                          · Pub/Sub is at-least-once. Dedupe by email_message_id using a Redis Set with 7-day TTL.

                                                          Security

                                                          · Always verify the OIDC token's aud claim matches PUBSUB_AUDIENCE.
                                                          · Reject requests without Authorization: Bearer.
                                                          · Never log raw email bodies at INFO level — they contain PII. Log only the parsed fields.

                                                          ---

                                                          UI / UX SPEC

                                                          Layout (mobile-first)

                                                          ```
                                                          ┌────────────────────────────────┐
                                                          │ FLUX          [date] [🌙]      │  ← header
                                                          ├────────────────────────────────┤
                                                          │  Total Balance                 │
                                                          │  ₹1,23,456.78                  │  ← hero
                                                          │  ▲ ₹4,200 this month           │
                                                          │  [Income] [Expense] [Entries]  │  ← 3 stat pills
                                                          ├────────────────────────────────┤
                                                          │ [Add][History][Charts][Budget][Goals] ← tabs
                                                          ├────────────────────────────────┤
                                                          │  Panel content                 │
                                                          └────────────────────────────────┘
                                                          ```

                                                          Design Language

                                                          · Minimal, dense, technical. Think Vercel dashboard meets a trading terminal.
                                                          · Monospace (Space Mono) for all numbers, dates, and labels.
                                                          · Sans (DM Sans) for descriptions and body text.
                                                          · Subtle 1px borders, no heavy shadows.
                                                          · Background grid pattern (44px cells) using linear-gradient — very low opacity.
                                                          · Accent colour: #00e5ff (cyan) in dark mode, #0284c7 (blue) in light.
                                                          · All numeric displays use font-variant-numeric: tabular-nums.

                                                          Micro-interactions

                                                          · Tabs: 200ms ease transition on colour and background.
                                                          · Category chips: scale 0.96 on tap, green flash for 300ms on selection.
                                                          · Balance amount: 300ms colour transition when it changes.
                                                          · Budget bars: 500ms cubic-bezier(0.4, 0, 0.2, 1) width animation.
                                                          · Toast: spring ease cubic-bezier(0.34, 1.4, 0.64, 1).

                                                          Accessibility

                                                          · All interactive elements keyboard-focusable.
                                                          · aria-label on icon-only buttons.
                                                          · aria-live="polite" on the toast container.
                                                          · Colour contrast ≥ 4.5:1 in both themes.

                                                          ---

                                                          ₹ FORMATTING RULES (CRITICAL)

                                                          Never use $ or USD. Never use Western grouping (1,234,567). Indian grouping is 1,23,456.78 — the last 3 digits are grouped, then groups of 2.

                                                          ```javascript
                                                          const inr = new Intl.NumberFormat('en-IN', {
                                                            style: 'currency', currency: 'INR',
                                                              minimumFractionDigits: 0, maximumFractionDigits: 2
                                                              });
                                                              inr.format(123456.78); // "₹1,23,456.78"
                                                              ```

                                                              ```python
                                                              def format_inr(amount: float) -> str:
                                                                  """Format a number as Indian Rupees with lakh/crore grouping."""
                                                                      # ... use locale-aware formatting
                                                                      ```

                                                                      · For values ≥ ₹1,00,000 in compact contexts (chart axes, stat pills), use notation: 'compact' which yields ₹1.2L / ₹1.2Cr in en-IN.
                                                                      · Negative amounts: −₹50 (use the minus sign U+2212, not hyphen).
                                                                      · Always two decimals in transaction lists, zero decimals in large aggregates.

                                                                      ---

                                                                      FLEXIBILITY & EXTENSION REQUIREMENTS

                                                                      The design must make these future changes trivial:

                                                                      1. Add a new bank parser — drop a new regex into parsing/regex_patterns.py with a test fixture. No other file changes.
                                                                      2. Swap storage — set STORAGE_BACKEND=postgres in .env. The StorageBackend ABC defines save_transaction, list_transactions, save_budget, etc. Implement PostgresStorage and register it in a factory.
                                                                      3. Add a new notification channel (e.g., WhatsApp, Telegram) — implement a Notifier ABC with a send(event) method. The parser worker calls notifier.send(parsed_tx) after publishing to Redis. Add TelegramNotifier without touching the worker.
                                                                      4. Add multi-user support — AuthProvider already abstracts this. NoAuthProvider returns a single tenant ID; FirebaseAuthProvider returns user.uid. All storage calls take a tenant_id.
                                                                      5. Add a mobile app — the API is REST + SSE. A React Native / Flutter client can consume the same endpoints. No backend changes.
                                                                      6. Add ML categorisation — categoriser.py exposes categorise(merchant, amount). Today it's keyword-based. Tomorrow, swap in a scikit-learn classifier or an embedding-based nearest-neighbour. The interface stays the same.
                                                                      7. Add currencies — the Transaction.currency field already exists and defaults to "INR". money.py has a format(amount, currency) function. Add a CurrencyConverter service when needed.
                                                                      8. Add recurring transaction detection — a new worker can subscribe to the same flux:transactions channel and flag patterns (e.g., same merchant + same amount ±5% every ~30 days). No coupling to existing code.
                                                                      9. Add export — a new API route GET /api/export?format=csv that streams from storage. Frontend adds a button. Nothing else changes.
                                                                      10. Replace Redis with Kafka/RabbitMQ — messaging.py defines a MessageBus ABC. Swap implementations via env var.

                                                                      Rule: Every "swap point" must be an abstract base class + a factory function reading from config.py. No if/else chains scattered across the codebase.

                                                                      ---

                                                                      SECURITY REQUIREMENTS

                                                                      · Never commit token.json, service-account.json, .env. Add to .gitignore and document how to obtain them.
                                                                      · OIDC verification on the Pub/Sub webhook is mandatory, not optional.
                                                                      · Rate-limit /api/classify and /api/transactions (Flask-Limiter, 100/min/IP).
                                                                      · Validate all inputs with Pydantic. Reject unknown fields.
                                                                      · Parameterised SQL only — never string-format SQL.
                                                                      · CORS: allow only the frontend origin(s) from env.
                                                                      · Sanitise user-provided strings before rendering in HTML (escHtml helper in JS; Jinja auto-escape on server).
                                                                      · Log PII-free: log transaction_id, amount, bank — never email bodies or full merchant strings with account numbers.

                                                                      ---

                                                                      ERROR HANDLING & OBSERVABILITY

                                                                      · Structured logging (JSON) with a request_id on every API call and every worker message.
                                                                      · /health returns { status, gmail_watch_expires_at, redis_connected, db_connected }.
                                                                      · Expose Prometheus metrics at /metrics (optional but recommended): transactions_parsed_total, parse_failures_total, sse_clients_connected, gmail_webhook_latency_seconds.
                                                                      · On any unhandled exception, log the traceback and return a generic 500 with a request_id the user can quote.
                                                                      · Frontend: every fetch wrapped in a helper that shows a toast on failure and retries once on network error.

                                                                      ---

                                                                      TESTING REQUIREMENTS

                                                                      · Unit tests for parsing/ covering at least 15 real-world bank alert samples (include the fixtures in tests/fixtures/emails/).
                                                                      · Integration test for the full webhook → parser → Redis → SSE flow, using InMemoryBus instead of real Redis.
                                                                      · Frontend: no formal test framework required, but include a ?demo=1 query param that loads 30 fake transactions so the UI can be evaluated without backend setup.
                                                                      · Target: pytest passes cleanly on a fresh clone with no external services running (use fakes).

                                                                      ---

                                                                      DELIVERABLES

                                                                      Produce the complete codebase with:

                                                                      1. All files listed in the project structure above, fully implemented — no # TODO stubs in core paths.
                                                                      2. docker-compose.yml that starts the entire stack with docker compose up --build.
                                                                      3. .env.example with every required variable documented in comments.
                                                                      4. README.md with:
                                                                         · 5-minute quickstart (Docker path)
                                                                            · Manual setup path (no Docker)
                                                                               · How to set up GCP Pub/Sub and Gmail OAuth
                                                                                  · How to add a new bank parser
                                                                                     · How to swap storage backends
                                                                                        · Architecture diagram (ASCII is fine)
                                                                                        5. gcp/setup.sh — idempotent setup script for Pub/Sub.
                                                                                        6. tests/ — passing pytest suite with fixtures.
                                                                                        7. Inline docstrings on every public function and class explaining why, not just what.

                                                                                        ---

                                                                                        CONSTRAINTS & NON-GOALS

                                                                                        · No Python web framework other than Flask. (FastAPI is acceptable if you prefer, but stay consistent.)
                                                                                        · No JS build step. The frontend must run by opening index.html in a browser (with the API running separately). No webpack, no Vite, no npm.
                                                                                        · No external paid services except the optional LLM fallback (which must be off by default and gated behind LLM_FALLBACK_ENABLED=true).
                                                                                        · No eval(), no innerHTML with unsanitised user input.
                                                                                        · No account aggregator (Setu/Finvu) integration in v1 — document it as a v2 path in the README.
                                                                                        · No mobile native apps — this is a web app only.

                                                                                        ---

                                                                                        APPENDIX: MERCHANT → CATEGORY KEYWORD MAP (SEED DATA)

                                                                                        Include this as seed data in parsing/categoriser.py. Extend as needed.

                                                                                        ```python
                                                                                        MERCHANT_CATEGORIES = {
                                                                                            # Groceries
                                                                                                "BIGBASKET": "Groceries", "GROFERS": "Groceries", "ZEPTO": "Groceries",
                                                                                                    "BLINKIT": "Groceries", "DMART": "Groceries", "RELIANCE FRESH": "Groceries",
                                                                                                        "MORE RETAIL": "Groceries", "SPENCERS": "Groceries",

                                                                                                            # Food
                                                                                                                "SWIGGY": "Food", "ZOMATO": "Food", "DOMINOS": "Food", "MCDONALDS": "Food",
                                                                                                                    "KFC": "Food", "BURGER KING": "Food", "PIZZA HUT": "Food", "STARBUCKS": "Food",
                                                                                                                        "CHAI POINT": "Food", "HALDIRAM": "Food",

                                                                                                                            # Transport
                                                                                                                                "OLA": "Transport", "UBER": "Transport", "RAPIDO": "Transport",
                                                                                                                                    "IRCTC": "Transport", "REDBUS": "Transport", "METRO": "Transport",
                                                                                                                                        "FASTAG": "Transport", "PETROL": "Transport", "HP PETROL": "Transport",
                                                                                                                                            "INDIAN OIL": "Transport", "BPCL": "Transport",

                                                                                                                                                # Shopping
                                                                                                                                                    "AMAZON": "Shopping", "FLIPKART": "Shopping", "MYNTRA": "Shopping",
                                                                                                                                                        "AJIO": "Shopping", "NYKAA": "Shopping", "MEESHO": "Shopping",
                                                                                                                                                            "DECATHLON": "Shopping", "CROMA": "Shopping", "VIJAY SALES": "Shopping",

                                                                                                                                                                # Bills
                                                                                                                                                                    "AIRTEL": "Bills", "JIO": "Bills", "VODAFONE": "Bills", "VI ": "Bills",
                                                                                                                                                                        "BSNL": "Bills", "TATA POWER": "Bills", "ADANI ELECTRICITY": "Bills",
                                                                                                                                                                            "BESCOM": "Bills", "MSEB": "Bills", "GAS": "Bills", "INDANE": "Bills",

                                                                                                                                                                                # Entertainment
                                                                                                                                                                                    "NETFLIX": "Entertainment", "SPOTIFY": "Entertainment", "HOTSTAR": "Entertainment",
                                                                                                                                                                                        "PRIME VIDEO": "Entertainment", "SONYLIV": "Entertainment", "ZEE5": "Entertainment",
                                                                                                                                                                                            "BOOKMYSHOW": "Entertainment", "PVR": "Entertainment", "INOX": "Entertainment",

                                                                                                                                                                                                # Health
                                                                                                                                                                                                    "PHARMEASY": "Health", "APOLLO": "Health", "1MG": "Health", "NETMEDS": "Health",
                                                                                                                                                                                                        "PRACTO": "Health", "CULT FIT": "Health", "GYM": "Health",

                                                                                                                                                                                                            # Education
                                                                                                                                                                                                                "BYJU": "Education", "UNACADEMY": "Education", "COURSERA": "Education",
                                                                                                                                                                                                                    "UDEMY": "Education", "VEDANTU": "Education", "SCHOOL FEES": "Education",

                                                                                                                                                                                                                        # Travel
                                                                                                                                                                                                                            "MAKEMYTRIP": "Travel", "GOIBIBO": "Travel", "YATRA": "Travel",
                                                                                                                                                                                                                                "IXIGO": "Travel", "AIRBNB": "Travel", "OYO": "Travel", "TRIVAGO": "Travel",

                                                                                                                                                                                                                                    # Rent
                                                                                                                                                                                                                                        "RENT": "Rent", "LANDLORD": "Rent", "HOUSING": "Rent", "NOBROKER": "Rent",

                                                                                                                                                                                                                                            # Investment
                                                                                                                                                                                                                                                "ZERODHA": "Investment", "GROWW": "Investment", "UPSTOX": "Investment",
                                                                                                                                                                                                                                                    "MUTUAL FUND": "Investment", "SIP": "Investment", "ANGEL ONE": "Investment",
                                                                                                                                                                                                                                                    }
                                                                                                                                                                                                                                                    ```

                                                                                                                                                                                                                                                    ---

                                                                                                                                                                                                                                                    APPENDIX: SAMPLE BANK ALERT FORMATS (FOR PARSER TESTS)

                                                                                                                                                                                                                                                    ```
                                                                                                                                                                                                                                                    HDFC:  "Rs.450.00 debited from A/c XX1234 on 15-04-25 to VPA grocery@ybl (UPI/412839). Avl bal: Rs.12,340.00"
                                                                                                                                                                                                                                                    ICICI: "INR 1,200.00 debited from A/c XX5678 on 15-Apr-25. Info: UPI/OLA-CABS@icici. Avl Bal: INR 8,900.00"
                                                                                                                                                                                                                                                    SBI:   "Rs.500.00 has been debited from A/c XX9012 to UPI/SWIGGY@ybl on 15Apr25. Ref No 412839001."
                                                                                                                                                                                                                                                    Axis:  "INR 250.00 spent on your Axis Bank Card ending 3456 at ZOMATO on 15-04-2025."
                                                                                                                                                                                                                                                    Kotak: "Rs.1,000.00 debited from Kotak A/c XX7890 on 15-04-25 towards UPI payment to merchant@kotak."
                                                                                                                                                                                                                                                    ```

                                                                                                                                                                                                                                                    ---

                                                                                                                                                                                                                                                    FINAL INSTRUCTION

                                                                                                                                                                                                                                                    Build the full application. Start by outputting the file tree, then write each file in full. Do not skip files. Do not use placeholders like # ...rest of code.... If a file exceeds your output limit, split it across multiple responses but keep going until the codebase is complete and docker compose up --build would succeed.

                                                                                                                                                                                                                                                    Prioritise correctness of the Gmail → parser → categorisation pipeline above all else. A user must be able to pay ₹50 via UPI, and within 30 seconds see a prompt in FLUX asking what the payment was for.

                                                                                                                                                                                                                                                    Begin.