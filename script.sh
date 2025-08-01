# Add a script that glues all the steps together.

#!/bin/bash
set -e

# Prereqs: AWS CLI, Terraform ≥1.0, Python 3.11+, and uv (`pip install uv`)

# ---- 1. Provision core infrastructure --------------------------------------
cd step1-infrastructure
./scripts/deploy.sh              # runs terraform init/plan/apply
cd ..

# ---- 2. Train & register the customer-segmentation model --------------------
cd step2-model-build-deploy
uv sync                           # install Python deps from pyproject.toml
uv run python src/pipeline.py --action deploy   # upload pipeline definition
uv run python src/pipeline.py --action run      # start a training job
cd ..

# ---- 3. Deploy Bedrock-powered Lambda --------------------------------------
cd task3-genai-lambda
uv run python deploy_lambda.py \
  --function-name genmab-bedrock \
  --role-arn arn:aws:iam::<ACCOUNT_ID>:role/lambda-bedrock-exec \
  --model-id anthropic.claude-instant-v1 \
  --update-if-exists
cd ..

# ---- 4. Smoke test the Lambda ----------------------------------------------
cd task3-genai-lambda
./test_lambda.sh
cd ..