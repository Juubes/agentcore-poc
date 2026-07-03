"""Cognito hosted-UI OAuth endpoints: authorize redirect, code exchange, logout."""
import urllib.parse

import config
from adapters import http


def authorize_url(redirect_uri, state, code_challenge):
    q = urllib.parse.urlencode({
        "response_type": "code", "client_id": config.PORTAL_CLIENT_ID,
        "redirect_uri": redirect_uri, "scope": "openid profile email",
        "state": state, "code_challenge": code_challenge,
        "code_challenge_method": "S256"})
    return f"{config.COGNITO_DOMAIN}/oauth2/authorize?{q}"


def exchange_code(code, redirect_uri, code_verifier):
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code", "client_id": config.PORTAL_CLIENT_ID,
        "code": code, "redirect_uri": redirect_uri,
        "code_verifier": code_verifier}).encode()
    return http.request("POST", f"{config.COGNITO_DOMAIN}/oauth2/token",
                        {"Content-Type": "application/x-www-form-urlencoded"}, data)


def logout_url(return_to):
    """Ends the hosted-UI SSO session too, so the next sign-in prompts again."""
    back = urllib.parse.quote(return_to, safe="")
    return (f"{config.COGNITO_DOMAIN}/logout"
            f"?client_id={config.PORTAL_CLIENT_ID}&logout_uri={back}")
