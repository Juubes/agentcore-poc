"""PKCE sign-in against the corporate IdP."""
import hashlib
import json
import os

import b64url
from adapters import cognito
from domain.session import Session


def start(redirect_uri):
    """Returns (authorize_url, pkce) — pkce goes into a short-lived signed cookie."""
    verifier = b64url.encode(os.urandom(48))
    challenge = b64url.encode(hashlib.sha256(verifier.encode()).digest())
    state = b64url.encode(os.urandom(16))
    return cognito.authorize_url(redirect_uri, state, challenge), \
        {"v": verifier, "s": state}


def finish(params, pkce, redirect_uri):
    """Exchange the callback code. Returns (Session, None) or (None, error)
    where error is "state" (bad/missing state or PKCE) or "exchange"."""
    code = params.get("code")
    if not code or not pkce or params.get("state") != pkce.get("s"):
        return None, "state"
    status, raw = cognito.exchange_code(code, redirect_uri, pkce["v"])
    if status != 200:
        return None, "exchange"
    session = Session.from_access_token(json.loads(raw)["access_token"])
    if session.expired:
        # An opaque/malformed access token parses to exp=0; surface an error
        # instead of setting a cookie that silently reads as signed-out.
        return None, "exchange"
    return session, None
