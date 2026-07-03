# Headless verification

Verify per-user authorization from the terminal, no browser needed. Fill in the
placeholders from the stack outputs and the demo password you gave
`scripts/setup-demo.sh`:

```bash
export AWS_REGION=eu-west-1
CLIENT_ID=<UserPoolClientId>   GATEWAY_URL=<GatewayUrl>   PW=$DEMO_PASSWORD

tok(){ aws cognito-idp initiate-auth --client-id "$CLIENT_ID" \
  --auth-flow USER_PASSWORD_AUTH --auth-parameters "USERNAME=$1,PASSWORD=$PW" \
  --region "$AWS_REGION" --query 'AuthenticationResult.AccessToken' --output text; }
call(){ curl -sS -X POST "$GATEWAY_URL" -H "Authorization: Bearer $1" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2025-11-25" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"internal-api___${2:-listDocuments}\",\"arguments\":{}}}"; }

call "$(tok alice)" listDocuments   # engineering documents
call "$(tok bob)"   listDocuments   # finance documents
call "$(tok alice)" listCustomers   # [], customers are finance-only
```

Expected: alice (engineering) and bob (finance) call the same tool and get
different, group-scoped records; alice's `listCustomers` returns an empty list.
A call without a bearer token returns `401`.
