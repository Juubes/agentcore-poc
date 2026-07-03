"""Connecting a provider: trigger the gateway's own 3LO flow, then finalize it
after the user consents.

Why drive the GATEWAY's flow instead of calling AgentCore Identity under the
portal's own workload identity: the token vault is workload-scoped and the
gateway's workload identity is service-linked (un-borrowable), so a token
vaulted under the portal's workload is invisible to the gateway. The portal
therefore triggers the gateway's flow with the user's JWT and completes exactly
that session with exactly that JWT — the one the gateway minted its workload
token from.
"""
from adapters import agentcore, gateway
from domain.connection import Outcome, interpret_reply


def initiate(session, provider) -> Outcome:
    """Probe/trigger the provider's 3LO through the gateway, as this user."""
    status, reply = gateway.call_tool(session.access_token, provider.tool)
    return interpret_reply(reply, status)


def complete(session, consent_session):
    """Finalize a consented session. Returns (http_status, raw_body)."""
    return agentcore.complete_resource_token_auth(consent_session,
                                                  session.access_token)
