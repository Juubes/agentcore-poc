"""Connections portal: Lambda entrypoint and HTTP routing.

Self-service onboarding for per-user third-party 3LO (e.g. GitHub), so the
gateway can serve each user's own token:

  1. The user signs in via the corporate IdP (Cognito hosted UI, PKCE); the
     portal now holds their access-token JWT.
  2. "Connect" calls a provider tool through the gateway as that user. With no
     vaulted token, the gateway starts its own 3LO flow and replies with a
     consent URL carrying a request_uri.
  3. The portal sends the browser through the consent URL; AgentCore captures
     the OAuth code and returns the browser to /connections/callback.
  4. The portal finalizes that exact session with that exact JWT
     (CompleteResourceTokenAuth), vaulting the token under the gateway's
     workload identity. Every later gateway call for this user is served.

application/connections.py explains why the gateway's own flow must be driven.
"""
import views
from adapters import cognito, cookies
from application import connections, login
from domain import providers
from domain.session import Session

NOTES = {"connected": "Connected ✓ — your gateway calls now use your own token.",
         "already": "Already connected ✓"}


def base_url(event) -> str:
    # Derived at runtime, not config: the function referencing its own API's
    # generated URL would be a CloudFormation circular dependency.
    return "https://" + event["requestContext"]["domainName"]


def login_redirect(event) -> str:
    return base_url(event) + "/login/callback"


def current_session(event):
    return Session.from_cookie(cookies.decode(cookies.read(event).get("session", "")))


def response(status, body=None, location=None, set_cookies=None):
    headers = {"Content-Type": "text/html; charset=utf-8"}
    if location:
        status, headers["Location"] = 302, location
    out = {"statusCode": status, "headers": headers, "body": body or ""}
    if set_cookies:
        out["cookies"] = set_cookies
    return out


def route_home(event):
    session = current_session(event)
    if not session:
        return response(200, views.signed_out())
    states = [(p, connections.initiate(session, p).kind == "connected")
              for p in providers.PROVIDERS.values()]
    note = NOTES.get((event.get("queryStringParameters") or {}).get("ok", ""), "")
    return response(200, views.home(session.user, session.groups, states, note))


def route_login(event):
    url, pkce = login.start(login_redirect(event))
    return response(302, location=url,
                    set_cookies=[cookies.header("pkce", cookies.encode(pkce), 600)])


def route_login_callback(event):
    params = event.get("queryStringParameters") or {}
    pkce = cookies.decode(cookies.read(event).get("pkce", ""))
    session, err = login.finish(params, pkce, login_redirect(event))
    if err == "state":
        return response(400, views.error("Login failed", "Invalid login state."))
    if err:
        return response(502, views.error("Login failed", "Token exchange failed."))
    return response(302, location="/", set_cookies=[
        cookies.header("session", cookies.encode(session.to_cookie()), 3600),
        cookies.header("pkce", "", 0)])


def route_logout(event):
    return response(302, location=cognito.logout_url(base_url(event) + "/"),
                    set_cookies=[cookies.header("session", "", 0)])


def route_connect(event, key):
    session = current_session(event)
    if not session:
        return response(302, location="/")
    provider = providers.PROVIDERS.get(key)
    if not provider:
        return response(404, views.error("Unknown provider", key))
    outcome = connections.initiate(session, provider)
    if outcome.kind == "connected":
        return response(302, location="/?ok=already")
    if outcome.kind == "authorize":
        # Persist the session the user is about to consent to; the callback must
        # finalize exactly this one (a fresh trigger would have no OAuth code).
        pending = cookies.encode({"provider": key,
                                  "session_uri": outcome.consent_session})
        return response(302, location=outcome.authorize_url,
                        set_cookies=[cookies.header("pending", pending, 600)])
    return response(502, views.error("Couldn't start connection", outcome.detail))


def route_connect_callback(event):
    session = current_session(event)
    pending = cookies.decode(cookies.read(event).get("pending", ""))
    if not session or not pending or not pending.get("session_uri"):
        return response(400, views.error("Connection failed",
                                         "Session expired — start over."))
    status, raw = connections.complete(session, pending["session_uri"])
    clear = [cookies.header("pending", "", 0)]
    if status == 200:
        return response(302, location="/?ok=connected", set_cookies=clear)
    return response(502, views.error("Connection failed",
                    f"Completion failed ({status}): "
                    f"{raw.decode('utf-8', 'replace')[:300]}"),
                    set_cookies=clear)


ROUTES = {"/": route_home,
          "/login": route_login,
          "/login/callback": route_login_callback,
          "/logout": route_logout,
          "/connections/callback": route_connect_callback}


def handler(event, _ctx):
    path = (event.get("rawPath") or "/").rstrip("/") or "/"
    try:
        if path.startswith("/connect/"):
            return route_connect(event, path.rsplit("/", 1)[-1])
        route = ROUTES.get(path)
        if route:
            return route(event)
        return response(404, views.error("Not found", "No such page."))
    except Exception as e:  # never leak a stack trace to the browser
        return response(500, views.error("Error",
                        f"Something went wrong: {type(e).__name__}"))
