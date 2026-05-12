"""Parse a HAR file from store reconnaissance.

Extracts all XHR/Fetch requests, groups by endpoint pattern,
and outputs a summary to docs/store_api.md.

Usage:
    uv run python scripts/parse_har.py [path/to/traffic.har]
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

HAR_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "docs" / "store_traffic.har"
OUTPUT_PATH = HAR_PATH.parent / "store_api.md"


def parse_har():
    with open(HAR_PATH) as f:
        har = json.load(f)

    entries = har["log"]["entries"]

    api_calls = []
    for entry in entries:
        req = entry["request"]
        resp = entry["response"]
        url = req["url"]
        parsed = urlparse(url)

        if not parsed.hostname:
            continue

        content_type = ""
        for header in resp["headers"]:
            if header["name"].lower() == "content-type":
                content_type = header["value"]
                break

        is_api = (
            "json" in content_type
            or "xml" in content_type
            or req["method"] in ("POST", "PUT", "DELETE", "PATCH")
            or "/api/" in url
            or "/rest/" in url
            or "/graphql" in url
        )

        if is_api or req["method"] != "GET":
            req_body = ""
            if req.get("postData"):
                req_body = req["postData"].get("text", "")[:500]

            resp_body = ""
            if resp.get("content", {}).get("text"):
                resp_body = resp["content"]["text"][:500]

            cookies = [c["name"] for c in req.get("cookies", [])]

            api_calls.append(
                {
                    "method": req["method"],
                    "url": url,
                    "path": parsed.path,
                    "status": resp["status"],
                    "content_type": content_type,
                    "request_body": req_body,
                    "response_preview": resp_body,
                    "cookies": cookies,
                    "request_headers": {
                        h["name"]: h["value"]
                        for h in req["headers"]
                        if h["name"].lower()
                        in (
                            "authorization",
                            "x-csrf-token",
                            "x-requested-with",
                            "content-type",
                            "cookie",
                        )
                    },
                }
            )

    by_path = defaultdict(list)
    for call in api_calls:
        by_path[call["path"]].append(call)

    lines = [
        "# Store API Endpoints (reverse-engineered)\n",
        f"Captured {len(api_calls)} API calls across {len(by_path)} unique paths.\n",
    ]

    for path, calls in sorted(by_path.items()):
        first = calls[0]
        lines.append(f"\n## `{first['method']} {path}`\n")
        lines.append(f"- Status: {first['status']}")
        lines.append(f"- Content-Type: {first['content_type']}")
        lines.append(f"- Called {len(calls)} time(s)")
        if first["cookies"]:
            lines.append(f"- Cookies sent: {', '.join(first['cookies'][:5])}")
        if first["request_headers"]:
            lines.append("- Notable headers:")
            for k, v in first["request_headers"].items():
                lines.append(
                    f"  - `{k}`: `{v[:80]}...`" if len(v) > 80 else f"  - `{k}`: `{v}`"
                )
        if first["request_body"]:
            lines.append(f"\n**Request body:**\n```json\n{first['request_body']}\n```")
        if first["response_preview"]:
            lines.append(
                f"\n**Response preview:**\n```json\n{first['response_preview']}\n```"
            )

    output = "\n".join(lines)
    OUTPUT_PATH.write_text(output)
    print(f"Written to {OUTPUT_PATH}")
    print("\nTop endpoints by frequency:")
    for path, calls in sorted(by_path.items(), key=lambda x: -len(x[1]))[:15]:
        print(f"  {len(calls):3d}x  {calls[0]['method']:6s} {path}")


if __name__ == "__main__":
    parse_har()
