"""Group-based authorization: a caller sees only records tagged with one of
their IdP groups."""
import base64
import json


def visible(records, groups):
    return [r for r in records if r["group"] in groups]


def claims(token):
    """Decode the JWT payload for identity claims. No signature check here: the
    gateway validated this token at inbound and IAM-signed the call that
    delivered it (production would re-verify via JWKS or use OBO)."""
    if not token or token.count(".") != 2:
        return {}
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}
