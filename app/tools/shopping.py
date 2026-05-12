"""Tool for interacting with the grocery store via GraphQL."""

import json
import os

from app.clients.store import StoreClient

_CLIENT: StoreClient | None = None


def _get_client() -> StoreClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = StoreClient(
            username=os.environ.get("STORE_USERNAME", ""),
            password=os.environ.get("STORE_PASSWORD", ""),
            store_code=os.environ.get("STORE_CODE", ""),
        )
    return _CLIENT


def store_graphql(query: str, variables: str = "{}") -> str:
    """Execute a GraphQL query or mutation on the grocery store.

    Load the store-api skill first to see available queries and
    field structures. Auth and cart ID are handled automatically.

    Args:
        query: The GraphQL query or mutation string.
        variables: JSON string of variables (e.g. '{"search": "latte", "pageSize": 5}').

    Returns:
        The JSON response data from the API.
    """
    client = _get_client()
    try:
        vars_dict = json.loads(variables) if variables else {}
    except json.JSONDecodeError:
        return f"Invalid JSON in variables: {variables}"
    try:
        data = client.execute_graphql(query, vars_dict)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"GraphQL error: {e}"
