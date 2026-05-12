# grocery-agent

A personal grocery assistant that plans meals, builds shopping carts on your online grocery store, and remembers your preferences across conversations.

Built with ❤️ with [`agents-cli`](https://github.com/google/agents-cli) on top of [Google ADK](https://google.github.io/adk-docs/) and the [A2A protocol](https://a2a-protocol.org/). Uses [`a2a-gateway`](https://github.com/eliasecchig/a2a-gateway) to bridge Telegram. It nudges you when it's time to restock.

![grocery-agent demo](grocery-agent.gif)

## What it does

It plans 2-3 dinners at a time, suggesting recipes based on your diet, what's in season, and what you've bought before. It then searches your store's catalog, picks products and quantities, and waits for you to confirm before adding anything to your cart.

A running shopping list lives in a Google Doc — say "add milk to the list" any time and the agent appends it. The same doc holds your preferences (brands, staples, dietary constraints), so the agent gets sharper as it learns your habits.

Cloud Scheduler kicks the agent every couple of days. It plans a grocery run on its own and sends you the proposal via Telegram.

## How it works

```
                                     ┌─────────────────┐
                                     │  Google Docs    │
                                     │ (preferences &  │
                                     │  shopping list) │
                                     └────────▲────────┘
                                              │
┌──────────┐     ┌─────────────┐     ┌────────┴────────┐     ┌─────────────────┐
│ Telegram │◄───►│ a2a-gateway │◄───►│ grocery-agent   │◄───►│ Grocery Store   │
└──────────┘     └─────────────┘     └─────────────────┘     └─────────────────┘
                                              ▲
                                              │
                                     ┌─────────────────┐
                                     │ Cloud Scheduler │
                                     │ (periodic nudge)│
                                     └─────────────────┘
```

The agent loads two ADK skills on demand: `store-api` (GraphQL queries against the store) and `grocery-doc` (the Google Doc that holds preferences and the shopping list).

## Get started

You'll need [uv](https://docs.astral.sh/uv/), the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install), a GCP project with Vertex AI enabled, an account on a grocery store with a GraphQL API, and a blank Google Doc for the agent's memory.

Everything else goes through [`agents-cli`](https://github.com/google/agents-cli):

```bash
# Install the CLI (one time)
uv tool install google-agents-cli

# Install project dependencies
agents-cli install

# Configure your store and credentials (see "Configure your environment" below)
cp .env.example .env

# Run locally
agents-cli playground
```

The playground gives you a web UI to chat with the agent. Try "what's in season?" or "add eggs to the list".

## Configure your environment

Fill `.env` with the values below. They become Secret Manager entries on `make deploy`.

### Store

| Variable | How to get it |
|---|---|
| `STORE_GRAPHQL_URL` | Your store's GraphQL endpoint. Find it in browser devtools (network tab) while shopping, or run `uv run --with playwright python scripts/auto_recon.py <store-url> <user> <pass>` to discover it. `scripts/parse_har.py` does the same from a saved HAR file. |
| `STORE_CART_URL` | The cart URL the agent links to after building a cart. |
| `STORE_CODE` | Magento store view code, often `default` or a country code. Visible in the `Store:` header of GraphQL requests. |
| `STORE_USERNAME` / `STORE_PASSWORD` | Your shopping account credentials. |

The default client is Magento 2 GraphQL. For another backend, swap `app/clients/store.py`. The `store_graphql` tool interface stays the same.

### Google Doc

| Variable | How to get it |
|---|---|
| `GROCERY_BRAIN_DOC_ID` | Create a blank Google Doc. The ID is the part of the URL between `/d/` and `/edit`. |

### Google OAuth (Docs API)

The agent reads and writes your Google Doc through your account, so you need an OAuth refresh token.

1. In the [GCP Console](https://console.cloud.google.com/apis/credentials), create an **OAuth 2.0 Client ID** of type **Desktop app**. Copy the values into `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`.
2. Enable the **Google Docs API** for the project.
3. Generate a refresh token at the [OAuth Playground](https://developers.google.com/oauthplayground/):
   - Click the gear icon, check **"Use your own OAuth credentials"**, paste your client ID and secret.
   - In step 1, authorize the `https://www.googleapis.com/auth/documents` scope.
   - In step 2, click **"Exchange authorization code for tokens"** and copy the refresh token into `GOOGLE_OAUTH_REFRESH_TOKEN`.

### Telegram

| Variable | How to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Talk to [@BotFather](https://t.me/BotFather): `/newbot`, follow prompts. |
| `NUDGE_RECIPIENT_ID` | Your numeric chat ID. [@userinfobot](https://t.me/userinfobot) replies with it. Then `/start` your own bot once so it can DM you. |

### After `make deploy`: push values into Secret Manager

`make deploy` creates the Secret Manager entries but leaves them empty. Push your `.env` values in afterward:

```bash
for SECRET in STORE_USERNAME STORE_PASSWORD GROCERY_BRAIN_DOC_ID \
              GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN \
              TELEGRAM_BOT_TOKEN NUDGE_RECIPIENT_ID; do
  echo -n "$(grep "^$SECRET=" .env | cut -d= -f2-)" | \
    gcloud secrets versions add "$SECRET" --data-file=- \
      --project=$(gcloud config get-value project)
done
```

Restart the Cloud Run revision (or run `make deploy` again) to pick up the values.

## Deploy to Cloud Run

```bash
gcloud config set project <your-project-id>
make deploy STORE_GRAPHQL_URL=https://your-store.com/graphql
```

The deploy creates an Artifact Registry remote repository (`ghcr-remote`) that proxies `ghcr.io`, so Cloud Run can pull the public [`a2a-gateway`](https://github.com/eliasecchig/a2a-gateway) image. Override `GATEWAY_IMAGE=...` to point at your own image instead.

| Resource | Purpose |
|---|---|
| `grocery-agent` (Cloud Run) | the agent service |
| [`a2a-gateway`](https://github.com/eliasecchig/a2a-gateway) (Cloud Run) | bridges Telegram to the agent via A2A |
| Cloud SQL | session persistence |
| Secret Manager | credentials and OAuth tokens |
| Cloud Scheduler | triggers the nudge every 2 days at 8am |

Once it's up, point your Telegram bot's webhook at the gateway URL.

## Customize

| What | Where |
|---|---|
| Personality, diet rules, prompt | `app/agent.py` |
| Store backend (default: Magento 2 GraphQL) | `app/clients/store.py` — swap for any client; the `store_graphql` tool interface stays the same |
| Nudge schedule (default: every 2 days, 8am Europe/Rome) | `deployment/terraform/single-project/scheduler.tf` |
| Notification channel (default: Telegram) | `app/tools/telegram.py` |
| New skills | drop a directory under `app/skills/` with a `SKILL.md`. See [ADK skills docs](https://google.github.io/adk-docs/skills/) |

## Develop

```
app/
├── agent.py              # Agent definition, system prompt, skill loading
├── fast_api_app.py       # FastAPI server, A2A setup, nudge endpoint
├── clients/
│   └── store.py          # Magento 2 GraphQL client (auth, cart, search)
├── tools/                # ADK tools the agent can call
│   ├── shopping.py       # store_graphql — raw GraphQL against the store
│   ├── gdocs.py          # read_gdoc, write_gdoc
│   └── telegram.py       # send_telegram
├── skills/
│   ├── store-api/        # Store GraphQL schema reference
│   └── grocery-doc/      # Grocery doc usage guide
└── app_utils/            # Telemetry, typing helpers
deployment/terraform/     # Full IaC: Cloud Run, SQL, IAM, Scheduler, Secrets
tests/
├── eval/                 # ADK evaluation framework with custom rubrics
├── unit/
└── integration/
scripts/                  # Store API reconnaissance utilities
```

```bash
make dev               # Local server with hot reload
make playground        # ADK web UI
make test              # Run all tests
make lint              # ruff + codespell
agents-cli eval run    # Run evaluation suite
```
