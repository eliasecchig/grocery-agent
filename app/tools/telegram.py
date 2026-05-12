"""Tool for sending messages to Telegram via the a2a-gateway."""

import os

import google.auth.transport.requests
import google.oauth2.id_token
import httpx


def send_telegram(message: str) -> str:
    """Send a message via Telegram.

    Use this when you need to proactively notify the user — e.g. after
    building a cart on a schedule, or when you have a summary to share.

    Args:
        message: The message text to send.

    Returns:
        Confirmation or error.
    """
    gateway_url = os.environ.get("GATEWAY_URL")
    recipient_id = os.environ.get("NUDGE_RECIPIENT_ID")
    if not gateway_url or not recipient_id:
        return "Error: GATEWAY_URL or NUDGE_RECIPIENT_ID not configured."

    headers: dict[str, str] = {}
    try:
        auth_req = google.auth.transport.requests.Request()
        token = google.oauth2.id_token.fetch_id_token(auth_req, gateway_url)
        headers["Authorization"] = f"Bearer {token}"
    except Exception:
        pass

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{gateway_url}/push",
            json={
                "channel": "telegram",
                "recipient_id": recipient_id,
                "text": message,
            },
            headers=headers,
        )
        resp.raise_for_status()

    return "Message sent to Telegram."
