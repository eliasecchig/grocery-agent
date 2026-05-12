"""Tools for reading/writing a Google Doc."""

import os

from google.oauth2.credentials import Credentials

from app.clients.gdocs import GroceryDoc

_DOC_ID = os.environ.get("GROCERY_BRAIN_DOC_ID", "")

_mock_content: str = """\
== NEXT BUY ==

== PREFERENCES ==
"""


class _MockDoc:
    def read(self) -> str:
        return _mock_content

    def write(self, content: str) -> None:
        global _mock_content
        _mock_content = content


def _get_doc() -> GroceryDoc | _MockDoc:
    if not _DOC_ID:
        return _MockDoc()
    creds = Credentials(
        token=os.environ.get("GOOGLE_OAUTH_TOKEN", ""),
        refresh_token=os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", ""),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID", ""),
        client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
    )
    return GroceryDoc(document_id=_DOC_ID, credentials=creds)


def read_gdoc() -> str:
    """Read the shared Google Doc.

    Returns:
        The full text content of the document.
    """
    return _get_doc().read()


def write_gdoc(content: str) -> str:
    """Overwrite the shared Google Doc with new content.

    Read the doc first, make changes, then write the full text back.

    Args:
        content: The complete new document text.

    Returns:
        Confirmation message.
    """
    _get_doc().write(content)
    return "Document updated."
