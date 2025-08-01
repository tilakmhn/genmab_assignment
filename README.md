# Genmab ML Assignment

End-to-end example that takes you from raw AWS infrastructure to a production-ready
SageMaker pipeline **and** a Bedrock-powered serverless endpoint.

## Repository Structure
| Step | Folder | What it contains |
|------|--------|------------------|
| 1️⃣ | `step1-infrastructure/` | Terraform that creates S3 buckets, IAM roles and (optionally) SageMaker endpoints. |
| 2️⃣ | `step2-model-build-deploy/` | Customer-segmentation pipeline (feature engineering → training → model registration) built with SageMaker Pipelines. |
| 3️⃣ | `task3-genai-lambda/` | AWS Lambda + Amazon Bedrock (Claude-Instant-v1) for text-based insights. |

## Quick Start (Happy Path) - script.sh

```bash
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

# ---- 4. Smoke test the Lambda ----------------------------------------------
./test_lambda.sh                  # writes response.json
```

## Clean Up

```bash
# Remove infrastructure
cd step1-infrastructure
./scripts/destroy.sh

# Delete the Lambda if desired
aws lambda delete-function --function-name genmab-bedrock
```

## More Details
Open the README inside each step’s folder for configuration options, cost notes,
and troubleshooting tips.