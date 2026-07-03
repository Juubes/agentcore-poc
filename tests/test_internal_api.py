"""Internal API (src/internal_api/): per-group authorization and identity
handling."""
import base64
import json

import internal_api


def _token(claims):
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"header.{payload}.sig"  # 3-part; signature not verified at this layer


def _call(collection, claims=None):
    headers = {"x-user-token": _token(claims)} if claims else {}
    return internal_api.handler({"rawPath": f"/internal/{collection}",
                                 "headers": headers}, None)


def test_no_identity_is_401():
    assert _call("documents", claims=None)["statusCode"] == 401


def test_whitespace_only_token_is_401():
    r = internal_api.handler({"rawPath": "/internal/documents",
                              "headers": {"x-user-token": " "}}, None)
    assert r["statusCode"] == 401


def test_engineering_sees_only_engineering_documents():
    r = _call("documents", {"username": "alice", "cognito:groups": ["engineering"]})
    body = json.loads(r["body"])
    assert r["statusCode"] == 200
    assert {i["group"] for i in body["items"]} == {"engineering"}
    assert body["caller"] == "alice"


def test_finance_customers_visible_only_to_finance():
    eng = json.loads(_call("customers", {"cognito:groups": ["engineering"]})["body"])
    fin = json.loads(_call("customers", {"cognito:groups": ["finance"]})["body"])
    assert eng["items"] == []
    assert {i["name"] for i in fin["items"]} == {"Acme Corp", "Globex"}


def test_unknown_collection_is_404():
    assert _call("secrets", {"cognito:groups": ["engineering"]})["statusCode"] == 404


def test_multi_group_user_sees_union():
    r = _call("documents", {"cognito:groups": ["engineering", "finance"]})
    groups = {i["group"] for i in json.loads(r["body"])["items"]}
    assert groups == {"engineering", "finance"}
