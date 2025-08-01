#!/usr/bin/env python3
"""
SageMaker Pipeline for Customer Segmentation Model
"""

import boto3
import sagemaker
from sagemaker.sklearn.estimator import SKLearn
from sagemaker.workflow.parameters import ParameterInteger, ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import TrainingStep, CreateModelStep
from sagemaker.workflow.step_collections import RegisterModel  
from sagemaker.model import Model
from sagemaker.inputs import TrainingInput
import yaml
from sagemaker.lambda_helper import Lambda
from sagemaker.workflow.lambda_step import LambdaStep
import time


def load_config(config_file="pipeline_config.yaml"):
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def create_pipeline(
    region="us-east-1",
    role_arn=None,
    lambda_role_arn=None,
    bucket_name=None,
    project_name="clustering-model",
    environment="dev"
):
    """Create and return SageMaker Pipeline"""
    
    # Initialize SageMaker session
    sagemaker_session = sagemaker.Session()
    
    # Pipeline parameters
    n_clusters_param = ParameterInteger(name="NClusters", default_value=3)
    n_components_param = ParameterInteger(name="NComponents", default_value=1)
    data_file_param = ParameterString(name="DataFile", default_value="customer_segmentation_data.csv")
    training_instance_type_param = ParameterString(name="TrainingInstanceType", default_value="ml.m5.large")
    inference_instance_type_param = ParameterString(name="InferenceInstanceType", default_value="ml.t2.medium")
    
    # Training step
    sklearn_estimator = SKLearn(
        entry_point="train.py",
        source_dir="src",
        framework_version="1.2-1",
        py_version="py3",
        instance_type=training_instance_type_param,
        instance_count=1,
        role=role_arn,
        sagemaker_session=sagemaker_session,
        output_path=f"s3://{bucket_name}/training-output",
        hyperparameters={
            "n-clusters": n_clusters_param,
            "n-components": n_components_param,
            "data-file": data_file_param
        },
        metric_definitions=[
            {"Name": "silhouette_score", "Regex": "Silhouette Score: ([0-9\\.]+)"},
            {"Name": "calinski_harabasz_score", "Regex": "Calinski-Harabasz Index: ([0-9\\.]+)"},
            {"Name": "davies_bouldin_score", "Regex": "Davies-Bouldin Index: ([0-9\\.]+)"}
        ]
    )
    
    training_step = TrainingStep(
        name="CustomerSegmentationTraining",
        estimator=sklearn_estimator,
        inputs={
            "training": TrainingInput(
                s3_data=f"s3://{bucket_name}/data/",
                content_type="text/csv"
            )
        }
    )
    # Tell SageMaker where the source code lives locally; the SDK will
    # create a tar.gz and upload it, embedding the real S3 path in the
    # pipeline definition.
    model = Model(
        image_uri=sklearn_estimator.training_image_uri(),
        model_data=training_step.properties.ModelArtifacts.S3ModelArtifacts,
        role=role_arn,
        entry_point="inference.py",
        source_dir="src",                 # <── just the local folder
        sagemaker_session=sagemaker_session,
    )
    
    create_model_step = CreateModelStep(
        name="CreateCustomerSegmentationModel",
        model=model,
        inputs=sagemaker.inputs.CreateModelInput(
            instance_type=inference_instance_type_param
        )
    )
    
    # Model registration step (simplified without metrics)
    register_model_step = RegisterModel(
        name="RegisterCustomerSegmentationModel",
        estimator=sklearn_estimator,
        model_data=training_step.properties.ModelArtifacts.S3ModelArtifacts,
        content_types=["text/csv", "application/json"],
        response_types=["application/json"],
        inference_instances=["ml.t2.medium"],
        model_package_group_name=f"{project_name}-model-group",
        approval_status="PendingManualApproval"
    )

    deploy_lambda = Lambda(
        function_name       = f"{project_name}-deploy-lambda-{environment}",   # will be created if it doesn’t exist
        execution_role_arn  = lambda_role_arn,        # <-- NEW role created in step 1-B
        script              = "src/deploy_lambda.py",
        handler             = "deploy_lambda.lambda_handler",
        timeout             = 300,                    # 5 min
        s3_bucket           = bucket_name             # where the zipped code is uploaded
    )

    deploy_step = LambdaStep(
        name        = "DeployEndpoint",
        lambda_func = deploy_lambda,
        inputs      = {
            "model_name"           : create_model_step.properties.ModelName,
            "endpoint_config_name" : f"{project_name}-endpoint-config-{environment}-{int(time.time())}",
            "endpoint_name"        : f"{project_name}-endpoint-{environment}-{int(time.time())}",
            "instance_type"        : inference_instance_type_param,
            "instance_count"       : 1,
        }
    )    
    # Create pipeline
    pipeline = Pipeline(
        name=f"{project_name}-pipeline-{environment}",
        parameters=[
            n_clusters_param,
            n_components_param,
            data_file_param,
            training_instance_type_param,
            inference_instance_type_param
        ],
        steps=[
            training_step,
            create_model_step,
            register_model_step,
            deploy_step
        ],
        sagemaker_session=sagemaker_session
    )
    return pipeline


def deploy_pipeline(
    region="us-east-1",
    role_arn=None,
    lambda_role_arn=None,
    bucket_name=None,
    project_name="clustering-model",
    environment="dev"
):
    """Deploy the pipeline"""
    
    # Create pipeline
    pipeline = create_pipeline(
        region=region,
        role_arn=role_arn,
        lambda_role_arn=lambda_role_arn,
        bucket_name=bucket_name,
        project_name=project_name,
        environment=environment
    )
    
    # Upsert pipeline
    print("Creating/updating pipeline...")
    pipeline.upsert(role_arn=role_arn)
    print(f"Pipeline created: {pipeline.name}")
    
    return pipeline


def run_pipeline(
    pipeline_name=None,
    region="us-east-1",
    project_name="clustering-model",
    environment="dev",
    parameters=None
):
    """Execute the pipeline"""
    
    if not pipeline_name:
        pipeline_name = f"{project_name}-pipeline-{environment}"
    
    sm_client = boto3.client('sagemaker')
    response = sm_client.start_pipeline_execution(
    PipelineName=pipeline_name,
    PipelineParameters=[
        {'Name': k, 'Value': str(v)} for k, v in (parameters or {}).items()
    ])
    execution_arn = response['PipelineExecutionArn']
    print(f"Execution ARN: {execution_arn}")
    
    return execution_arn


if __name__ == "__main__":
    import argparse
    import yaml
    
    config = load_config("src/pipeline_config.yaml")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["deploy", "run"], required=True)
    parser.add_argument("--role-arn", type=str, default=config["role_arn"])
    parser.add_argument("--lambda-role-arn", type=str, default=config.get("lambda_role_arn", ""))
    parser.add_argument("--bucket-name", type=str, default=config["bucket_name"])
    parser.add_argument("--project-name", type=str, default=config["project_name"])
    parser.add_argument("--environment", type=str, default=config["environment"])
    parser.add_argument("--region", type=str, default=config["region"])
    
    args = parser.parse_args()
    
    if args.action == "deploy":
        pipeline = deploy_pipeline(
            region=args.region,
            role_arn=args.role_arn,
            lambda_role_arn=args.lambda_role_arn,
            bucket_name=args.bucket_name,
            project_name=args.project_name,
            environment=args.environment
        )
        print(f"Pipeline deployed successfully: {pipeline.name}")
        
    elif args.action == "run":
        execution = run_pipeline(
            region=args.region,
            project_name=args.project_name,
            environment=args.environment
        )
        print(f"Pipeline execution started: {execution}")