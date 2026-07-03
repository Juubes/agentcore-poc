"""HTML rendering. Identity-derived values are escaped here, at output."""
import html


def page(title, inner):
    return f"""<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>{title}</title>
<style>
 body{{font:16px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
   max-width:640px;margin:6vh auto;padding:0 20px;color:#1a1a2e;background:#fafafc}}
 h1{{font-size:22px}} .muted{{color:#6b7280;font-size:13px}}
 .btn{{display:inline-block;background:#4f46e5;color:#fff;text-decoration:none;
   padding:9px 16px;border-radius:8px;font-size:14px}}
 .btn:hover{{background:#4338ca}}
 .badge{{background:#dcfce7;color:#166534;padding:7px 13px;border-radius:8px;
   font-size:13px;font-weight:600}}
 .card{{display:flex;align-items:center;justify-content:space-between;gap:16px;
   border:1px solid #e5e7eb;background:#fff;border-radius:12px;padding:16px;margin:12px 0}}
 .ok{{border-color:#16a34a;color:#166534}}
 a{{color:#4f46e5}} code{{background:#eef;padding:1px 5px;border-radius:4px}}
</style></head><body><h1>{title}</h1>{inner}
<p class=muted style=margin-top:40px>Governed AI-tool gateway · Amazon Bedrock AgentCore</p>
</body></html>"""


def signed_out():
    return page("Connections portal",
        "<p>Connect your third-party accounts so AI tools can reach them "
        "<b>through the governed gateway</b> — audited, on your own identity, "
        "no personal access tokens.</p>"
        "<p><a class='btn' href='/login'>Sign in with your corporate account</a></p>")


def home(user, groups, provider_states, note=""):
    """provider_states: iterable of (Provider, connected: bool)."""
    note_html = f"<div class='card ok'>{html.escape(note)}</div>" if note else ""
    user = html.escape(str(user or ""))
    groups = html.escape(", ".join(groups or []) or "none")
    rows = "".join(_provider_row(p, c) for p, c in provider_states)
    return page("Connections portal",
        f"{note_html}<p>Signed in as <b>{user}</b> "
        f"<span class='muted'>(groups: {groups})</span> · "
        f"<a href='/logout'>sign out</a></p>{rows}")


def _provider_row(provider, connected):
    if connected:
        action = ("<span class='badge'>Connected &#10003;</span>"
                  f"<a class='muted' style='margin-left:12px' "
                  f"href='/connect/{provider.key}'>reconnect</a>")
    else:
        action = f"<a class='btn' href='/connect/{provider.key}'>Connect</a>"
    return (f"<div class='card'><div><b>{provider.label}</b><div class='muted'>"
            f"3LO OAuth · vaulted under your gateway identity</div></div>{action}</div>")


def error(title, detail):
    return page(title, f"<p>{html.escape(str(detail or ''))}</p>"
                       f"<p><a href='/'>Back</a></p>")
