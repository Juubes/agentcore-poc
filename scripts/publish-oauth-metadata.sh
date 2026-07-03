#!/usr/bin/env bash
set -euo pipefail

# Publishes a corrected OAuth authorization-server metadata document.
# Cognito serves no RFC 8414 metadata (/.well-known/oauth-authorization-server 400s),
# and its OIDC discovery omits code_challenge_methods_supported and never offers the
# "none" token-endpoint auth method a public + PKCE client needs. This document
# restates the hosted-domain endpoints with those fields corrected.
# No secrets. Run once after deploy (and again if the pool or domain changes).

cd "$(dirname "$0")/.."
: "${AWS_REGION:=eu-west-1}"
: "${STACK:=governed-gateway}"
export AWS_REGION

out(){ aws cloudformation describe-stacks --region "$AWS_REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }

POOL_ID=$(out UserPoolId)
DOMAIN=$(out CognitoDomain)
BUCKET=${STACK}-$(aws sts get-caller-identity --query Account --output text)-oauth
ISSUER="https://cognito-idp.${AWS_REGION}.amazonaws.com/${POOL_ID}"

cat > /tmp/oauth-authorization-server.json <<JSON
{
  "issuer": "${ISSUER}",
  "authorization_endpoint": "${DOMAIN}/oauth2/authorize",
  "token_endpoint": "${DOMAIN}/oauth2/token",
  "jwks_uri": "${ISSUER}/.well-known/jwks.json",
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "code_challenge_methods_supported": ["S256"],
  "token_endpoint_auth_methods_supported": ["none"],
  "scopes_supported": ["openid", "profile", "email"],
  "subject_types_supported": ["public"]
}
JSON

aws s3 cp /tmp/oauth-authorization-server.json \
  "s3://${BUCKET}/oauth-authorization-server.json" \
  --content-type application/json --region "$AWS_REGION"

echo "Published: $(out AuthServerMetadataUrl)"
