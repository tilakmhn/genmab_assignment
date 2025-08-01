#!/bin/bash

set -e

# 1. Deploy the pipeline
echo "Deploying pipeline..."
uv run python ./src/pipeline.py --action deploy

# 2. Run the pipeline and capture the execution ARN
echo "Starting pipeline execution..."
EXEC_ARN=$(uv run python ./src/pipeline.py --action run | grep "Execution ARN:" | awk '{print $3}')
echo "Pipeline execution started: $EXEC_ARN"