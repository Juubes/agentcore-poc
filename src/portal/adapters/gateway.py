"""MCP client for the gateway: a single tools/call, used to probe a provider's
connection state and to trigger its 3LO flow."""
import json

import config
from adapters import http

# Sentinel JSON-RPC id: tells the RESPONSE interceptor not to rewrite this
# elicitation — the portal needs the real request_uri, not a link to itself.
# Must equal src/interceptor/interceptor.py ONBOARDING_ID — separate Lambda
# zips force the duplication; tests/test_interceptor.py asserts they match.
ONBOARDING_ID = "__portal_onboarding__"


def call_tool(access_token, tool):
    """Returns (http_status, parsed JSON-RPC reply or None) — SSE or plain JSON."""
    body = json.dumps({"jsonrpc": "2.0", "id": ONBOARDING_ID,
                       "method": "tools/call",
                       "params": {"name": tool, "arguments": {"per_page": 1}}}).encode()
    headers = {"Authorization": f"Bearer {access_token}",
               "Content-Type": "application/json",
               "Accept": "application/json, text/event-stream",
               "MCP-Protocol-Version": "2025-11-25"}
    status, raw = http.request("POST", config.GATEWAY_URL, headers, body)
    return status, _last_json(raw.decode("utf-8", "replace"))


def _last_json(text):
    obj = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            line = line[5:].strip()
        if line.startswith("{"):
            try:
                obj = json.loads(line)
            except Exception:
                continue
    return obj
