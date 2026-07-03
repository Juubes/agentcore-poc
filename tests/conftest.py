"""Puts each Lambda's source root on sys.path (mirroring the Lambda task root)
and sets the environment the modules read at import time."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

os.environ.update(
    AWS_REGION="eu-west-1",
    COGNITO_DOMAIN="https://d.auth.eu-west-1.amazoncognito.com",
    PORTAL_CLIENT_ID="cid",
    GATEWAY_URL="https://gw",
    COOKIE_SECRET="unit-test-secret",
    PORTAL_URL="https://portal.example.com",
    AWS_ACCESS_KEY_ID="a", AWS_SECRET_ACCESS_KEY="b", AWS_SESSION_TOKEN="t",
)

for d in ("src/portal", "src/interceptor", "src/internal_api"):
    sys.path.insert(0, os.path.join(ROOT, d))
