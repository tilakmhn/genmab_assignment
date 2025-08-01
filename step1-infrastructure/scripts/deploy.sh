#!/bin/bash

set -e

echo "Deploying SageMaker Customer Segmentation Infrastructure..."

cd terraform

echo "Initializing Terraform with backend configuration..."
terraform init -backend-config=backend.conf

echo "Validating Terraform configuration..."
terraform validate

echo "Planning deployment..."
terraform plan

echo "Applying deployment..."
terraform apply

echo "Deployment completed successfully!"
terraform output