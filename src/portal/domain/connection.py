"""Interpreting the gateway's reply to a provider tool call: either a token is
already vaulted for this caller, or AgentCore wants the user's OAuth consent."""
import urllib.parse
from dataclasses import dataclass


@dataclass(frozen=True)
class Outcome:
    kind: str                    # "connected" | "authorize" | "error"
    authorize_url: str = None    # consent URL the user's browser must visit
    consent_session: str = None  # AgentCore request_uri; finalized on callback
    detail: str = None


def interpret_reply(reply, status=None) -> Outcome:
    if reply is None:
        return Outcome("error", detail="unparseable gateway response"
                       + (f" ({status})" if status else ""))
    error = reply.get("error")
    if not error:
        # The tool call succeeded, so a token is already vaulted for this user.
        return Outcome("connected")
    for e in (error.get("data") or {}).get("elicitations") or []:
        url = e.get("url", "")
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if "request_uri" in qs:
            return Outcome("authorize", authorize_url=url,
                           consent_session=qs["request_uri"][0])
    # `or`, not a .get default: the gateway can send an explicit null message.
    return Outcome("error", detail=error.get("message") or "gateway error")
