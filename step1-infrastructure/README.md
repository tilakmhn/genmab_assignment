# Infrastructure Deployment

Terraform infrastructure for SageMaker ML Infrastructure deployment with S3 backend.

## Prerequisites

- AWS CLI configured
- Terraform >= 1.0
- S3 remote backend configured in `backend.conf`

## Quick Start

```bash
# 1. Configure variables by editing or updating this file
# Note: Ideally there will be env specific .tfvars and CI/CD pipelines will pick the correct one based on which env the CI/CD pipeline is deploying.
cp terraform.tfvars

# 2. Deploy infrastructure
./scripts/deploy.sh

# 3. Destroy infrastucture
./scripts/destroy.sh
```

## Scripts

- `deploy.sh` - Deploy/update infrastructure
- `destroy.sh` - Destroy all resources

## Outputs

- `data_bucket_name` - Upload training data here
- `model_bucket_name` - Upload trained models here  
- `sagemaker_endpoint_url` - API endpoint (when model deployed)

## Two-Phase Deployment

**Phase 1**: Infrastructure only (S3, IAM)
- Leave `model_data_url = ""` in terraform.tfvars
- No SageMaker resources created (saves cost)

**Phase 2**: ML model deployment  
- Set `model_data_url` after training
- Creates SageMaker model and endpoint

## Core Resources Created

### 📦 **S3 Buckets**
- `data-bucket` - Training data storage
- `models-bucket` - ML model artifacts storage
- Features: Versioning, encryption, public access blocked

### 🔐 **IAM Resources**
- `sagemaker-execution-role` - Service role for SageMaker
- `sagemaker-s3-policy` - Access to project S3 buckets
- `sagemaker-logs-policy` - CloudWatch logging permissions
- `sagemaker-ecr-policy` - Container image access

### 🤖 **SageMaker Resources** (when model_data_url set)
- `sagemaker-model` - ML model definition
- `endpoint-configuration` - Hardware specs (ml.t2.medium)
- `sagemaker-endpoint` - Live API for predictions

### ⚖️ **Auto Scaling Resources** (when enable_auto_scaling = true)
- `auto-scaling-target` - Scaling configuration
- `auto-scaling-policy` - Scaling rules (target: 70 invocations/instance)