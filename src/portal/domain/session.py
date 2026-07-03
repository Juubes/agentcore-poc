"""The signed-in caller, built from the IdP access token's claims."""
import json
import time
from dataclasses import dataclass

import b64url


def jwt_claims(token: str) -> dict:
    """Payload only, no signature check: the portal never grants access on these
    claims — the gateway re-validates the token cryptographically on every call."""
    try:
        return json.loads(b64url.decode(token.split(".")[1]))
    except Exception:
        return {}


@dataclass
class Session:
    access_token: str
    user: str
    groups: list
    exp: int

    @classmethod
    def from_access_token(cls, access_token):
        c = jwt_claims(access_token)
        return cls(access_token=access_token,
                   user=c.get("username") or c.get("cognito:username") or c.get("sub"),
                   groups=c.get("cognito:groups", []),
                   exp=c.get("exp", 0))

    @property
    def expired(self):
        return self.exp < time.time()

    def to_cookie(self) -> dict:
        return {"at": self.access_token, "user": self.user,
                "groups": self.groups, "exp": self.exp}

    @classmethod
    def from_cookie(cls, data):
        """Rebuild from a verified cookie payload; None if absent or expired."""
        if not data:
            return None
        session = cls(access_token=data.get("at", ""), user=data.get("user"),
                      groups=data.get("groups") or [], exp=data.get("exp", 0))
        return None if session.expired else session
