# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import google.auth
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentExtension
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
)
from fastapi import FastAPI
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.cloud import logging as google_cloud_logging

from app.agent import app as adk_app
from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

setup_telemetry()
_, project_id = google.auth.default()
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)

# Artifact bucket for ADK (created by Terraform, passed via env var)
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
artifact_service = (
    GcsArtifactService(bucket_name=logs_bucket_name)
    if logs_bucket_name
    else InMemoryArtifactService()
)


def _build_db_url() -> str | None:
    """Build async PostgreSQL URL for Cloud SQL via Unix socket."""
    conn_name = os.environ.get("DB_CONNECTION_NAME")
    db_name = os.environ.get("DB_NAME")
    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASS")
    if not conn_name or not db_name or not db_pass:
        return None
    from urllib.parse import quote

    encoded_user = quote(db_user, safe="")
    encoded_pass = quote(db_pass, safe="")
    encoded_instance = conn_name.replace(":", "%3A")
    return (
        f"postgresql+asyncpg://{encoded_user}:{encoded_pass}@"
        f"/{db_name}"
        f"?host=/cloudsql/{encoded_instance}"
    )


db_url = _build_db_url()

if db_url:
    from google.adk.sessions import DatabaseSessionService

    session_service = DatabaseSessionService(db_url=db_url)
else:
    session_service = InMemorySessionService()

task_store = InMemoryTaskStore()

runner = Runner(
    app=adk_app,
    artifact_service=artifact_service,
    session_service=session_service,
)

request_handler = DefaultRequestHandler(
    agent_executor=A2aAgentExecutor(runner=runner),
    task_store=task_store,
)

A2A_RPC_PATH = f"/a2a/{adk_app.name}"


async def build_dynamic_agent_card() -> AgentCard:
    """Builds the Agent Card dynamically from the root_agent."""
    agent_card_builder = AgentCardBuilder(
        agent=adk_app.root_agent,
        capabilities=AgentCapabilities(
            streaming=True,
            extensions=[
                AgentExtension(
                    uri="https://google.github.io/adk-docs/a2a/a2a-extension/",
                    description="Ability to use the new agent executor implementation",
                ),
            ],
        ),
        rpc_url=f"{os.getenv('APP_URL', 'http://0.0.0.0:8000')}{A2A_RPC_PATH}",
        agent_version=os.getenv("AGENT_VERSION", "0.1.0"),
    )
    agent_card = await agent_card_builder.build()
    return agent_card


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    agent_card = await build_dynamic_agent_card()
    a2a_app = A2AFastAPIApplication(agent_card=agent_card, http_handler=request_handler)
    a2a_app.add_routes_to_app(
        app_instance,
        agent_card_url=f"{A2A_RPC_PATH}{AGENT_CARD_WELL_KNOWN_PATH}",
        rpc_url=A2A_RPC_PATH,
        extended_agent_card_url=f"{A2A_RPC_PATH}{EXTENDED_AGENT_CARD_PATH}",
    )
    yield


app = FastAPI(
    title="grocery-agent",
    description="API for interacting with the Agent grocery-agent",
    lifespan=lifespan,
)


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


NUDGE_PROMPT = (
    "You are being triggered on a schedule. Plan a grocery run for the next 2-3 days. "
    "Read the grocery doc for preferences and pending items, check order history, "
    "check what's in season, plan 2-3 dinner recipes, and build a cart on the store. "
    "Once the cart is ready, use send_telegram to send the user a short, friendly message. "
    "DO NOT say 'weekly check in' or anything like that — just jump straight into "
    "what you planned: the recipes, the cart items with prices, the total, and "
    "a link to the store's cart page to finalize. "
    "End with something like 'Reply if you want to change anything!'"
)


@app.post("/trigger/nudge")
async def trigger_nudge() -> dict[str, str]:
    """Triggered by Cloud Scheduler via Pub/Sub.

    Runs the agent with a canned prompt to autonomously plan a grocery
    run, build a cart, and send the summary to Telegram.
    """
    from google.genai import types

    nudge_session = await session_service.create_session(
        app_name=adk_app.name,
        user_id="scheduler",
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=NUDGE_PROMPT)],
    )

    events = []
    async for event in runner.run_async(
        user_id="scheduler",
        session_id=nudge_session.id,
        new_message=message,
    ):
        events.append(event)

    return {"status": "nudge_completed", "events": str(len(events))}


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
