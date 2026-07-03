#!/usr/bin/env bash
set -euo pipefail

# Attach the interceptor Lambda to the gateway at both the REQUEST and RESPONSE
# points. This MUST run after every CloudFormation deploy: interceptors are an
# update-gateway/API concern, not a CloudFormation property, so any CFN update to
# the Gateway resource re-states its config WITHOUT the interceptor and silently
# drops it. (Symptom: internal-api tools return 401 "no verified caller identity"
# while the OAUTH/GitHub path still works, because only internal-api relies on the
# REQUEST interceptor.) Idempotent.

cd "$(dirname "$0")/.."
: "${AWS_REGION:=eu-west-1}"
: "${STACK:=governed-gateway}"
export AWS_REGION

INTERCEPTOR_ARN=$(aws cloudformation describe-stacks --region "$AWS_REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='InterceptorArn'].OutputValue" --output text)
GATEWAY_ID=$(aws bedrock-agentcore-control list-gateways --region "$AWS_REGION" \
  --query "items[?name=='${STACK}'].gatewayId | [0]" --output text)

echo "attaching interceptor $INTERCEPTOR_ARN onto gateway $GATEWAY_ID"
aws bedrock-agentcore-control get-gateway --region "$AWS_REGION" \
  --gateway-identifier "$GATEWAY_ID" > /tmp/gw.json
python3 - "$INTERCEPTOR_ARN" <<'PY'
import json, subprocess, sys, os
arn = sys.argv[1]
gw = json.load(open("/tmp/gw.json"))
args = [
  "aws","bedrock-agentcore-control","update-gateway",
  "--region", os.environ["AWS_REGION"],
  "--gateway-identifier", gw["gatewayId"],
  "--name", gw["name"],
  "--role-arn", gw["roleArn"],
  "--protocol-type", gw["protocolType"],
  "--authorizer-type", gw["authorizerType"],
  "--authorizer-configuration", json.dumps(gw["authorizerConfiguration"]),
  "--interceptor-configurations", json.dumps([{
      "interceptor": {"lambda": {"arn": arn}},
      "interceptionPoints": ["REQUEST", "RESPONSE"],
      "inputConfiguration": {"passRequestHeaders": True},
  }]),
]
if gw.get("description"):
    args += ["--description", gw["description"]]
if gw.get("protocolConfiguration"):
    args += ["--protocol-configuration", json.dumps(gw["protocolConfiguration"])]
if gw.get("exceptionLevel"):
    args += ["--exception-level", gw["exceptionLevel"]]
subprocess.run(args, check=True)
print("  interceptor attached (REQUEST + RESPONSE, passRequestHeaders=true)")
PY
