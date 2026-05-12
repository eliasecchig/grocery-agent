# Coding Agent Guide

## Prerequisites

Install the CLI (one-time):
```bash
uv tool install google-agents-cli
```

---

## Project Overview

This is a personal grocery assistant built with Google ADK and the A2A protocol. It plans meals, builds shopping carts on an online grocery store (via GraphQL), and remembers user preferences in a Google Doc.

### Key files
- `app/agent.py` — agent definition, system prompt, skill loading
- `app/fast_api_app.py` — FastAPI server, A2A setup, scheduled nudge endpoint
- `app/clients/store.py` — Magento 2 GraphQL client (auth, cart, search, orders)
- `app/tools/shopping.py` — `store_graphql` tool wrapping the store client
- `app/tools/gdocs.py` — `read_gdoc`, `write_gdoc` tools
- `app/tools/telegram.py` — `send_telegram` tool (via a2a-gateway)
- `app/skills/store-api/` — skill with GraphQL schema reference + seasonal data
- `app/skills/grocery-doc/` — skill for the shared grocery doc (long-term memory)

### Environment variables
All store-specific config is in env vars (see `.env.example`):
- `STORE_GRAPHQL_URL` — the store's GraphQL endpoint
- `STORE_CODE` — store code header for multi-store setups
- `STORE_USERNAME` / `STORE_PASSWORD` — store account credentials
- `GROCERY_BRAIN_DOC_ID` — Google Doc ID for preferences and shopping list

---

## Development Phases

### Phase 1: Understand Requirements
Before writing any code, understand the project's requirements, constraints, and success criteria.

### Phase 2: Build and Implement
Implement agent logic in `app/`. Use `agents-cli playground` for interactive testing. Iterate based on user feedback.

### Phase 3: The Evaluation Loop (Main Iteration Phase)
Start with 1-2 eval cases, run `agents-cli eval run`, iterate. Expect 5-10+ iterations. See the **Evaluation Guide** for metrics, evalset schema, LLM-as-judge config, and common gotchas.

### Phase 4: Pre-Deployment Tests
Run `uv run pytest tests/unit tests/integration`. Fix issues until all tests pass.

### Phase 5: Deploy to Dev
**Requires explicit human approval.** Run `agents-cli deploy` only after user confirms. See the **Deployment Guide** for details.

### Phase 6: Production Deployment
Ask the user: Option A (simple single-project) or Option B (full CI/CD pipeline with `agents-cli infra cicd`).

## Development Commands

| Command | Purpose |
|---------|---------|
| `agents-cli playground` | Interactive local testing |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests |
| `agents-cli eval run` | Run evaluation against evalsets |
| `agents-cli lint` | Check code quality |
| `agents-cli infra single-project` | Set up project infrastructure (Terraform) |
| `agents-cli deploy` | Deploy to dev |
| `agents-cli scaffold enhance` | Add deployment target or CI/CD to project |
| `agents-cli scaffold upgrade` | Upgrade project to latest version |

---

## Operational Guidelines for Coding Agents

- **Code preservation**: Only modify code directly targeted by the user's request. Preserve all surrounding code, config values (e.g., `model`), comments, and formatting.
- **NEVER change the model** unless explicitly asked.
- **Model 404 errors**: Fix `GOOGLE_CLOUD_LOCATION` (e.g., `global` instead of `us-east1`), not the model name.
- **ADK tool imports**: Import the tool instance, not the module: `from google.adk.tools.load_web_page import load_web_page`
- **Run Python with `uv`**: `uv run python script.py`. Run `agents-cli install` first.
- **Stop on repeated errors**: If the same error appears 3+ times, fix the root cause instead of retrying.
- **Terraform conflicts** (Error 409): Use `terraform import` instead of retrying creation.
