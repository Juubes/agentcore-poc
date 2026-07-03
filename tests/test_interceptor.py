"""Gateway interceptor (src/interceptor/): the two load-bearing behaviours.

REQUEST  — stamps the caller's JWT onto internal-api calls as X-User-Token.
RESPONSE — rewrites un-onboarded 3LO elicitations to the portal, but never
           the portal's own probe, and passes normal responses through.
"""
import interceptor


def _elicitation_event(rpc_id, tool="github___listMyRepositories"):
    return {"mcp": {
        "gatewayRequest": {"body": {"id": rpc_id, "method": "tools/call",
                                    "params": {"name": tool}}},
        "gatewayResponse": {"statusCode": 200, "body": {"error": {"code": -32042, "data": {
            "elicitations": [{"mode": "url",
                              "url": "https://bedrock-agentcore.eu-west-1.amazonaws.com/identities/oauth2/authorize?request_uri=urn:REAL"}]}}}}}}


def _url(resp):
    return resp["mcp"]["transformedGatewayResponse"]["body"]["error"]["data"]["elicitations"][0]["url"]


def test_request_stamps_identity_on_internal_api():
    ev = {"mcp": {"gatewayRequest": {
        "body": {"method": "tools/call", "params": {"name": "internal-api___listDocuments"}},
        "headers": {"Authorization": "Bearer JWT123"}}}}
    out = interceptor.handler(ev, None)
    assert out["mcp"]["transformedGatewayRequest"]["headers"] == {"X-User-Token": "JWT123"}


def test_request_ignores_non_internal_tools():
    ev = {"mcp": {"gatewayRequest": {
        "body": {"method": "tools/call", "params": {"name": "github___listMyRepositories"}},
        "headers": {"Authorization": "Bearer JWT123"}}}}
    out = interceptor.handler(ev, None)
    assert "headers" not in out["mcp"]["transformedGatewayRequest"]


def test_response_rewrites_client_elicitation_to_portal():
    out = interceptor.handler(_elicitation_event(rpc_id=1), None)
    assert _url(out) == "https://portal.example.com/connect/github"


def test_response_skips_portal_own_probe():
    out = interceptor.handler(_elicitation_event(rpc_id=interceptor.ONBOARDING_ID), None)
    assert "request_uri=urn:REAL" in _url(out)
    assert "portal.example.com" not in _url(out)


def test_onboarding_sentinel_matches_portal():
    # Two Lambdas, two zips, one contract: a one-sided rename would make the
    # interceptor rewrite the portal's own probe and break all onboarding.
    from adapters import gateway as portal_gateway
    assert interceptor.ONBOARDING_ID == portal_gateway.ONBOARDING_ID


def test_response_passes_through_success():
    ev = {"mcp": {"gatewayRequest": {"body": {"params": {"name": "x___y"}}},
                  "gatewayResponse": {"statusCode": 200, "body": {"result": {"ok": 1}}}}}
    out = interceptor.handler(ev, None)
    assert out["mcp"]["transformedGatewayResponse"]["body"]["result"] == {"ok": 1}
