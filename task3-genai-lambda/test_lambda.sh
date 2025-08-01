#!/bin/bash
set -e

FUNCTION_NAME="genmab-bedrock"
PAYLOAD='{"text":"Summarise Genmab in 50 words."}'

echo "Testing $FUNCTION_NAME..."

aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --cli-binary-format raw-in-base64-out \
  --payload "$PAYLOAD" \
  response.json

echo "Response:"
command -v jq &> /dev/null && jq . response.json || cat response.json