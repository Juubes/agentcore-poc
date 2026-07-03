"""Connections portal (src/portal/): cookie codec, session expiry, routing,
output escaping, and gateway reply interpretation."""
import app
from adapters import cognito, cookies, http
from application import connections, login
from domain.connection import Outcome, interpret_reply
from domain.providers import PROVIDERS
from domain.session import Session

GITHUB = PROVIDERS["github"]


def _event(path, cookie_list=None, qs=None):
    return {"rawPath": path, "cookies": cookie_list or [],
            "queryStringParameters": qs or {},
            "requestContext": {"http": {"method": "GET"},
                               "domainName": "abc.execute-api.eu-west-1.amazonaws.com"}}


def _session(**over):
    s = Session(access_token="AT", user="alice", groups=["engineering"],
                exp=9_999_999_999)
    for k, v in over.items():
        setattr(s, k, v)
    return s


def _session_cookie(**over):
    return "session=" + cookies.encode(_session(**over).to_cookie())


def test_cookie_roundtrip():
    c = cookies.encode({"a": 1, "b": "x"})
    assert cookies.decode(c) == {"a": 1, "b": "x"}


def test_cookie_rejects_tampering():
    c = cookies.encode({"user": "alice"})
    forged = c[:-4] + ("AAAA" if not c.endswith("AAAA") else "BBBB")
    assert cookies.decode(forged) is None


def test_expired_session_is_none():
    ev = _event("/", cookie_list=[_session_cookie(exp=1)])
    assert app.current_session(ev) is None


def test_anonymous_home_shows_sign_in():
    r = app.handler(_event("/"), None)
    assert r["statusCode"] == 200 and "Sign in" in r["body"]


def test_login_is_pkce_redirect():
    r = app.handler(_event("/login"), None)
    loc = r["headers"]["Location"]
    assert r["statusCode"] == 302
    assert "code_challenge_method=S256" in loc
    assert "redirect_uri=https%3A%2F%2Fabc.execute-api" in loc
    assert any(c.startswith("pkce=") for c in r.get("cookies", []))


def test_unknown_path_404():
    assert app.handler(_event("/nope"), None)["statusCode"] == 404


def test_connect_unknown_provider_404():
    r = app.handler(_event("/connect/nope", cookie_list=[_session_cookie()]), None)
    assert r["statusCode"] == 404


def test_callback_without_pending_is_400():
    r = app.handler(_event("/connections/callback",
                           cookie_list=[_session_cookie()]), None)
    assert r["statusCode"] == 400


def test_home_escapes_identity_claims(monkeypatch):
    monkeypatch.setattr(connections, "initiate", lambda s, p: Outcome("connected"))
    ev = _event("/", cookie_list=[_session_cookie(user="<script>x</script>",
                                                  groups=["<b>eng</b>"])])
    body = app.handler(ev, None)["body"]
    assert "<script>x</script>" not in body and "&lt;script&gt;" in body
    assert "<b>eng</b>" not in body


def test_home_shows_connected_badge_vs_connect_button(monkeypatch):
    monkeypatch.setattr(connections, "initiate", lambda s, p: Outcome("connected"))
    assert "Connected" in app.handler(_event("/", cookie_list=[_session_cookie()]), None)["body"]
    monkeypatch.setattr(connections, "initiate",
                        lambda s, p: Outcome("authorize", authorize_url="https://x"))
    body = app.handler(_event("/", cookie_list=[_session_cookie()]), None)["body"]
    assert ">Connect<" in body and "Connected" not in body


def test_initiate_parses_elicitation_session_uri(monkeypatch):
    sse = (b'event: message\n'
           b'data: {"jsonrpc":"2.0","id":"__portal_onboarding__","error":{"code":-32042,'
           b'"data":{"elicitations":[{"mode":"url","url":'
           b'"https://bedrock-agentcore.eu-west-1.amazonaws.com/identities/oauth2/authorize'
           b'?request_uri=urn%3Aietf%3Aparams%3Aoauth%3Arequest_uri%3AABC"}]}}}\n')
    monkeypatch.setattr(http, "request", lambda *a, **k: (200, sse))
    outcome = connections.initiate(_session(), GITHUB)
    assert outcome.kind == "authorize"
    assert outcome.consent_session == "urn:ietf:params:oauth:request_uri:ABC"


def test_initiate_reports_connected_on_success(monkeypatch):
    ok = b'data: {"jsonrpc":"2.0","id":1,"result":{"content":[]}}\n'
    monkeypatch.setattr(http, "request", lambda *a, **k: (200, ok))
    assert connections.initiate(_session(), GITHUB).kind == "connected"


def test_interpret_reply_error_without_elicitation():
    out = interpret_reply({"error": {"message": "boom"}})
    assert out.kind == "error" and out.detail == "boom"


def test_interpret_reply_null_message_gets_fallback_detail():
    out = interpret_reply({"error": {"message": None}})
    assert out.kind == "error" and out.detail == "gateway error"


def test_interpret_reply_unparseable_includes_status():
    out = interpret_reply(None, 503)
    assert out.kind == "error" and "(503)" in out.detail


def test_connect_error_page_renders_without_detail(monkeypatch):
    monkeypatch.setattr(connections, "initiate", lambda s, p: Outcome("error"))
    r = app.handler(_event("/connect/github", cookie_list=[_session_cookie()]), None)
    assert r["statusCode"] == 502  # Outcome.detail=None must not crash to a 500


def test_login_rejects_opaque_access_token(monkeypatch):
    monkeypatch.setattr(cognito, "exchange_code",
                        lambda *a: (200, b'{"access_token": "not-a-jwt"}'))
    session, err = login.finish({"code": "c", "state": "s"}, {"v": "v", "s": "s"},
                                "https://r")
    assert session is None and err == "exchange"
