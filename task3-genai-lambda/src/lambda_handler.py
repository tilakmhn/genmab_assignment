"""AWS Lambda handler for Amazon Bedrock text generation.

Usage: Set MODEL_ID, MAX_TOKENS, TEMPERATURE env vars. Send {"text": "prompt"} in event body.
Returns {"completion": "generated text"} or error response.
"""

import json
import os
import boto3

_BEDROCK = boto3.client("bedrock-runtime")
_MODEL_ID = os.environ.get("MODEL_ID", "anthropic.claude-v2")
_MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "400"))
_TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.7"))


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def lambda_handler(event: dict, context) -> dict:
    # Parse request body
    if isinstance(event.get("body"), str):
        try:
            payload = json.loads(event["body"] or "{}")
        except json.JSONDecodeError:
            return _response(400, {"error": "Invalid JSON"})
    else:
        payload = event.get("body") or event

    user_text = (payload or {}).get("text", "").strip()
    if not user_text:
        return _response(400, {"error": "'text' field required"})

    # Call Bedrock
    request = {
        "prompt": f"Human: {user_text}\n\nAssistant:",
        "max_tokens_to_sample": _MAX_TOKENS,
        "temperature": _TEMPERATURE,
        "stop_sequences": ["\n\nHuman:"],
    }

    try:
        response = _BEDROCK.invoke_model(
            modelId=_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request),
        )
        completion = json.loads(response["body"].read()).get("completion")
        return _response(200, {"completion": completion})
    except Exception as e:
        return _response(500, {"error": str(e)})