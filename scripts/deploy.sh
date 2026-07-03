#!/usr/bin/env bash
set -euo pipefail

# Package the Lambdas from src/ and deploy the stack.
# Secrets come from scripts/.env (gitignored): GithubClientId, GithubClientSecret.
# Idempotent: safe to re-run.

cd "$(dirname "$0")/.."
: "${AWS_REGION:=eu-west-1}"
: "${STACK:=governed-gateway}"
export AWS_REGION

[ -f scripts/.env ] && set -a && . scripts/.env && set +a
: "${GithubClientId:?set GithubClientId in scripts/.env}"
: "${GithubClientSecret:?set GithubClientSecret in scripts/.env}"

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ARTIFACTS="${STACK}-${ACCOUNT}-artifacts"

# Artifacts bucket for the packaged Lambda code (created once). us-east-1 rejects a
# LocationConstraint, so only pass it elsewhere.
if ! aws s3api head-bucket --bucket "$ARTIFACTS" 2>/dev/null; then
  echo "creating artifacts bucket $ARTIFACTS"
  if [ "$AWS_REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$ARTIFACTS" --region "$AWS_REGION" >/dev/null
  else
    aws s3api create-bucket --bucket "$ARTIFACTS" --region "$AWS_REGION" \
      --create-bucket-configuration "LocationConstraint=$AWS_REGION" >/dev/null
  fi
fi

echo "packaging..."
aws cloudformation package --template-file template.yaml \
  --s3-bucket "$ARTIFACTS" --output-template-file .packaged.yaml >/dev/null

echo "deploying stack $STACK..."
aws cloudformation deploy --template-file .packaged.yaml --stack-name "$STACK" \
  --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
  --region "$AWS_REGION" \
  --parameter-overrides \
    "GithubClientId=$GithubClientId" \
    "GithubClientSecret=$GithubClientSecret"

out(){ aws cloudformation describe-stacks --region "$AWS_REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
PORTAL_URL=$(out PortalUrl)
POOL_ID=$(out UserPoolId)
PORTAL_CLIENT=$(out PortalClientId)

# Register the real portal callback on the Cognito app client (it can't be set in
# the template without a circular dependency — see template.yaml PortalClient).
# Built as JSON so aws-cli v1 doesn't try to fetch the https:// URLs (cli_follow_urlparam).
echo "setting portal callback URL on Cognito client..."
python3 - "$POOL_ID" "$PORTAL_CLIENT" "$STACK" "$PORTAL_URL" > /tmp/portal-client.json <<'PY'
import json, sys
pool, cid, stack, url = sys.argv[1:5]
print(json.dumps({
    "UserPoolId": pool, "ClientId": cid, "ClientName": f"{stack}-portal",
    "SupportedIdentityProviders": ["COGNITO"],
    "AllowedOAuthFlowsUserPoolClient": True,
    "AllowedOAuthFlows": ["code"],
    "AllowedOAuthScopes": ["openid", "profile", "email"],
    "ExplicitAuthFlows": ["ALLOW_REFRESH_TOKEN_AUTH"],
    "CallbackURLs": [f"{url}/login/callback"],
    "LogoutURLs": [f"{url}/"],
}))
PY
aws cognito-idp update-user-pool-client --region "$AWS_REGION" \
  --cli-input-json file:///tmp/portal-client.json >/dev/null

# A CFN update to the Gateway re-states its config and drops the out-of-band
# interceptor, so always re-attach it here.
scripts/attach-interceptor.sh

echo
echo "Done. Portal URL: $PORTAL_URL"
echo "Next: scripts/setup-demo.sh (creates demo users), scripts/publish-oauth-metadata.sh"
