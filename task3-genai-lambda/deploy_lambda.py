"""Deploy Bedrock Lambda function using boto3."""

import argparse
import io
import pathlib
import zipfile
import boto3

ROOT_DIR = pathlib.Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"


def _build_zip(src_dir: pathlib.Path) -> bytes:
    """Return ZIP payload containing all files under src_dir."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in src_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(src_dir).as_posix())
    return buffer.getvalue()


def deploy(function_name: str, role_arn: str, model_id: str, 
          memory: int = 512, timeout: int = 15, region: str = None,
          update_if_exists: bool = False):
    """Create or update Lambda function."""
    client = boto3.client("lambda", region_name=region)
    zip_payload = _build_zip(SRC_DIR)
    env_vars = {"MODEL_ID": model_id}
    
    try:
        client.get_function(FunctionName=function_name)
        exists = True
    except client.exceptions.ResourceNotFoundException:
        exists = False

    if exists and update_if_exists:
        print(f"Updating '{function_name}'...")
        client.update_function_code(FunctionName=function_name, ZipFile=zip_payload, Publish=True)
        client.update_function_configuration(
            FunctionName=function_name, Environment={"Variables": env_vars},
            MemorySize=memory, Timeout=timeout)
    elif not exists:
        print(f"Creating '{function_name}'...")
        client.create_function(
            FunctionName=function_name, Runtime="python3.12", Role=role_arn,
            Handler="lambda_handler.lambda_handler", Code={"ZipFile": zip_payload},
            Description="Generative AI inference via Amazon Bedrock",
            Timeout=timeout, MemorySize=memory, Publish=True,
            Environment={"Variables": env_vars})
    else:
        print(f"Function '{function_name}' exists. Use --update-if-exists to update.")
        return
    
    print("Completed")


def main():
    parser = argparse.ArgumentParser(description="Deploy Bedrock Lambda")
    parser.add_argument("--function-name", required=True)
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--model-id", default="anthropic.claude-v2")
    parser.add_argument("--memory", type=int, default=512)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--region")
    parser.add_argument("--update-if-exists", action="store_true")
    
    args = parser.parse_args()
    deploy(args.function_name, args.role_arn, args.model_id, 
           args.memory, args.timeout, args.region, args.update_if_exists)


if __name__ == "__main__":
    main()