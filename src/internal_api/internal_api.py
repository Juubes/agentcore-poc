"""Mock internal system (documents / tickets / HR / CRM) behind the IAM-authed
HTTP API. Authorizes each request on the caller's IdP groups, taken from the
X-User-Token header the gateway interceptor injects."""
import json

from authorization import claims, visible
from records import DATA


def _resp(code, obj):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(obj)}


def handler(event, _ctx):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    parts = (headers.get("x-user-token") or "").split()
    identity = claims(parts[-1] if parts else "")
    if not identity:
        return _resp(401, {"error": "no verified caller identity"})
    groups = identity.get("cognito:groups", []) or []
    user = identity.get("username") or identity.get("sub")
    collection = (event.get("rawPath") or "/").rstrip("/").rsplit("/", 1)[-1]
    if collection not in DATA:
        return _resp(404, {"error": "unknown collection", "collection": collection})
    items = visible(DATA[collection], groups)
    # Structured audit line (CloudWatch): who reached what, on whose identity.
    print(json.dumps({"audit": "internal_api_access", "caller": user,
                      "groups": groups, "collection": collection,
                      "returned": len(items)}))
    return _resp(200, {"caller": user, "groups": groups,
                       "collection": collection, "items": items})
