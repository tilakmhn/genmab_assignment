#!/bin/bash

set -e

echo "Destroying SageMaker infrastructure..."

cd terraform

terraform init -backend-config=backend.conf
terraform destroy

echo "Infrastructure destroyed!"