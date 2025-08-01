"""Lambda to create/update SageMaker endpoints from pipeline.

Input: {"model_name", "endpoint_config_name", "endpoint_name", "instance_type", "instance_count"}
"""

import json
import boto3
from botocore.exceptions import ClientError

sm = boto3.client("sagemaker")


def lambda_handler(event, context):
    model_name = event["model_name"]
    config_name = event["endpoint_config_name"]
    endpoint_name = event["endpoint_name"]
    instance_type = event["instance_type"]
    instance_count = int(event.get("instance_count", 1))

    # Create endpoint config
    print(f"Creating config: {config_name}")
    sm.create_endpoint_config(
        EndpointConfigName=config_name,
        ProductionVariants=[{
            "VariantName": "AllTraffic",
            "ModelName": model_name,
            "InitialInstanceCount": instance_count,
            "InstanceType": instance_type,
        }]
    )

    # Check if endpoint exists
    try:
        sm.describe_endpoint(EndpointName=endpoint_name)
        exists = True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ValidationException":
            exists = False
        else:
            raise

    # Create or update endpoint
    if exists:
        print(f"Updating endpoint: {endpoint_name}")
        sm.update_endpoint(EndpointName=endpoint_name, EndpointConfigName=config_name)
        action = "update"
    else:
        print(f"Creating endpoint: {endpoint_name}")
        sm.create_endpoint(EndpointName=endpoint_name, EndpointConfigName=config_name)
        action = "create"

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Successfully triggered {action} of endpoint",
            "endpoint_name": endpoint_name,
        })
    }