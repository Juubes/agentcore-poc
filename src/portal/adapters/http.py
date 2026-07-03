"""Thin urllib wrapper — the portal is stdlib-only (no boto3/requests)."""
import urllib.error
import urllib.request


def request(method, url, headers=None, data=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
