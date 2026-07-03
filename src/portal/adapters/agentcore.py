"""The one AgentCore Identity call the portal makes, SigV4-signed by hand
(stdlib-only): CompleteResourceTokenAuth finalizes a gateway-initiated 3LO
session so the token vaults under the gateway's workload identity."""
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone

import config
from adapters import http

SERVICE = "bedrock-agentcore"


def complete_resource_token_auth(session_uri, user_token):
    host = f"{SERVICE}.{config.REGION}.amazonaws.com"
    path = "/identities/CompleteResourceTokenAuth"
    body = json.dumps({"sessionUri": session_uri,
                       "userIdentifier": {"userToken": user_token}}).encode()
    headers = _sigv4_headers(host, path, body)
    return http.request("POST", f"https://{host}{path}", headers, body)


def _sigv4_headers(host, path, body):
    ak = os.environ["AWS_ACCESS_KEY_ID"]
    sk = os.environ["AWS_SECRET_ACCESS_KEY"]
    st = os.environ.get("AWS_SESSION_TOKEN")

    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(body).hexdigest()

    signed_headers = "content-type;host;x-amz-content-sha256;x-amz-date"
    canon_headers = (f"content-type:application/json\n"
                     f"host:{host}\n"
                     f"x-amz-content-sha256:{payload_hash}\n"
                     f"x-amz-date:{amz_date}\n")
    if st:
        signed_headers += ";x-amz-security-token"
        canon_headers += f"x-amz-security-token:{st}\n"

    canon_req = "\n".join(["POST", path, "", canon_headers, signed_headers, payload_hash])
    scope = f"{date_stamp}/{config.REGION}/{SERVICE}/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope,
                         hashlib.sha256(canon_req.encode()).hexdigest()])

    def _hmac(key, msg):
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()

    k = _hmac(("AWS4" + sk).encode(), date_stamp)
    k = _hmac(k, config.REGION)
    k = _hmac(k, SERVICE)
    k = _hmac(k, "aws4_request")
    signature = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()

    headers = {"Content-Type": "application/json", "Host": host,
               "X-Amz-Date": amz_date, "X-Amz-Content-Sha256": payload_hash,
               "Authorization": (f"AWS4-HMAC-SHA256 Credential={ak}/{scope}, "
                                 f"SignedHeaders={signed_headers}, Signature={signature}")}
    if st:
        headers["X-Amz-Security-Token"] = st
    return headers
