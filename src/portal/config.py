"""Environment configuration, read once at Lambda init."""
import os

REGION = os.environ["AWS_REGION"]
COGNITO_DOMAIN = os.environ["COGNITO_DOMAIN"].rstrip("/")
PORTAL_CLIENT_ID = os.environ["PORTAL_CLIENT_ID"]
GATEWAY_URL = os.environ["GATEWAY_URL"]
COOKIE_SECRET = os.environ["COOKIE_SECRET"].encode()
