"""HMAC-signed cookies — the portal's only session state."""
import hashlib
import hmac
import json

import b64url
import config


def _sign(payload: str) -> str:
    return b64url.encode(hmac.new(config.COOKIE_SECRET, payload.encode(),
                                  hashlib.sha256).digest())


def encode(obj) -> str:
    payload = b64url.encode(json.dumps(obj, separators=(",", ":")).encode())
    return payload + "." + _sign(payload)


def decode(value):
    try:
        payload, sig = value.split(".", 1)
        if not hmac.compare_digest(sig, _sign(payload)):
            return None
        return json.loads(b64url.decode(payload))
    except Exception:
        return None


def read(event) -> dict:
    jar = {}
    for c in event.get("cookies") or []:
        if "=" in c:
            k, v = c.split("=", 1)
            jar[k.strip()] = v.strip()
    return jar


def header(name, value, max_age=3600) -> str:
    return (f"{name}={value}; Path=/; HttpOnly; Secure; SameSite=Lax; "
            f"Max-Age={max_age}")
