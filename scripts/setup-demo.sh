#!/usr/bin/env bash
set -euo pipefail

# Demo-user wiring the CloudFormation stack can't do: create alice/bob (Cognito
# can't set passwords in CFN) and assign their groups. Idempotent: safe to
# re-run, and the way to reset the demo passwords.

cd "$(dirname "$0")/.."
: "${AWS_REGION:=eu-west-1}"
: "${STACK:=governed-gateway}"
: "${DEMO_PASSWORD:?set DEMO_PASSWORD (the shared demo-user password, min 8 chars)}"
export AWS_REGION

out(){ aws cloudformation describe-stacks --region "$AWS_REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }

POOL_ID=$(out UserPoolId)
echo "pool=$POOL_ID"

mkuser(){ # username group
  local u="$1" g="$2"
  if ! aws cognito-idp admin-get-user --user-pool-id "$POOL_ID" --username "$u" \
        --region "$AWS_REGION" >/dev/null 2>&1; then
    aws cognito-idp admin-create-user --user-pool-id "$POOL_ID" --username "$u" \
      --message-action SUPPRESS --region "$AWS_REGION" >/dev/null
  fi
  aws cognito-idp admin-set-user-password --user-pool-id "$POOL_ID" --username "$u" \
    --password "$DEMO_PASSWORD" --permanent --region "$AWS_REGION" >/dev/null
  aws cognito-idp admin-add-user-to-group --user-pool-id "$POOL_ID" --username "$u" \
    --group-name "$g" --region "$AWS_REGION" >/dev/null
  echo "  user $u -> group $g"
}
echo "creating demo users..."
mkuser alice engineering
mkuser bob   finance

echo
echo "Done. Test per-user authorization: docs/VERIFY.md"
