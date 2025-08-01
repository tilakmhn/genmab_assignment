# Generative AI Lambda

AWS Lambda function that generates text summaries using Amazon Bedrock's Claude Instant model.

## Quick Start

```bash
# 1. Deploy the Lambda
uv run python deploy_lambda.py \
  --function-name genmab-bedrock \
  --role-arn arn:aws:iam::607274468492:role/lambda-bedrock-exec \
  --model-id anthropic.claude-instant-v1 \
  --update-if-exists

# 2. Test it
./test_lambda.sh
```

## Files

- `src/lambda_handler.py` - Lambda function code
- `deploy_lambda.py` - Deployment script (uses boto3)
- `test_lambda.sh` - Test script

## Pre-requisite
Make sure that you have enabled access to the foundational model, anthropic.claude-instant-v1 in this example otherwise you will get an error.