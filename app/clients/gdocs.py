"""Google Docs client for the shared grocery doc."""

import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class GroceryDoc:
    """Read/write the shared Google Doc used as a freeform grocery doc."""

    AGENT_SIGNATURE = "grocery-agent"

    def __init__(self, document_id: str, credentials: Credentials):
        self._doc_id = document_id
        self._service = build("docs", "v1", credentials=credentials)

    def read(self) -> str:
        """Read the full document text."""
        doc = self._service.documents().get(documentId=self._doc_id).execute()
        text_parts = []
        for element in doc.get("body", {}).get("content", []):
            paragraph = element.get("paragraph")
            if paragraph:
                for run in paragraph.get("elements", []):
                    text_run = run.get("textRun")
                    if text_run:
                        text_parts.append(text_run["content"])
        return "".join(text_parts)

    def write(self, content: str) -> None:
        """Overwrite the entire document body with new content."""
        end_index = self._get_end_index()
        requests = []
        if end_index > 2:
            requests.append(
                {"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end_index - 1}}}
            )
        requests.append({"insertText": {"location": {"index": 1}, "text": content}})
        self._service.documents().batchUpdate(
            documentId=self._doc_id, body={"requests": requests}
        ).execute()

    def _get_end_index(self) -> int:
        doc = self._service.documents().get(documentId=self._doc_id).execute()
        return doc["body"]["content"][-1]["endIndex"]

