"""Gateway interceptor, attached at both REQUEST and RESPONSE points by
scripts/attach-interceptor.sh (interceptors are an update-gateway concern,
not a CloudFormation property).

REQUEST   internal-api tool calls get the caller's already-validated IdP JWT
          forwarded as X-User-Token, so the backend can authorize per user.
RESPONSE  a bare MCP client can't complete AgentCore's 3LO authorize URL, so
          elicitations for un-onboarded providers are rewritten to point at
          the connections portal.
"""
import os

PORTAL_URL = os.environ.get("PORTAL_URL", "").rstrip("/")

# The portal tags its own onboarding probe with this JSON-RPC id; its
# elicitation must keep the real request_uri, not a link back to the portal.
# Must equal src/portal/adapters/gateway.py ONBOARDING_ID — separate Lambda
# zips force the duplication; tests/test_interceptor.py asserts they match.
ONBOARDING_ID = "__portal_onboarding__"


def _tool_name(request_body):
    return ((request_body.get("params") or {}).get("name")) or ""


def _provider(request_body):
    # Tool names are "<target>___<operation>"; the target is the provider key.
    name = _tool_name(request_body)
    return name.split("___", 1)[0] if "___" in name else ""


def transform_request(request):
    body = request.get("body") or {}
    headers = request.get("headers") or {}
    transformed = {"body": body}
    if body.get("method") == "tools/call" and _tool_name(body).startswith("internal-api"):
        # Custom header: the gateway owns outbound Authorization (its SigV4 credential).
        auth = headers.get("Authorization") or headers.get("authorization")
        if auth:
            transformed["headers"] = {"X-User-Token": auth.split()[-1]}
    return transformed


def transform_response(request_body, response):
    body = response.get("body") or {}
    if request_body.get("id") != ONBOARDING_ID:
        elicitations = (((body.get("error") or {}).get("data") or {})
                        .get("elicitations")) or []
        provider = _provider(request_body)
        for e in elicitations:
            url = e.get("url") or ""
            if e.get("mode") == "url" and "/identities/oauth2/authorize" in url \
                    and PORTAL_URL and provider:
                e["url"] = f"{PORTAL_URL}/connect/{provider}"
                e["message"] = (f"Connect {provider} once in your connections "
                                f"portal, then re-run this tool.")
    return {"body": body, "statusCode": response.get("statusCode", 200)}


def handler(event, _ctx):
    mcp = event.get("mcp") or {}
    request = mcp.get("gatewayRequest") or {}
    response = mcp.get("gatewayResponse")
    if response is not None:
        return {"interceptorOutputVersion": "1.0",
                "mcp": {"transformedGatewayResponse":
                        transform_response(request.get("body") or {}, response)}}
    return {"interceptorOutputVersion": "1.0",
            "mcp": {"transformedGatewayRequest": transform_request(request)}}
