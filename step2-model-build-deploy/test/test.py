import boto3
import json

runtime = boto3.client('sagemaker-runtime')

data = {
    "Age": 30,
    "Income": 50000,
    "Purchases": 10,
    "Gender": "Male"
}

response = runtime.invoke_endpoint(
    EndpointName='clustering-model-endpoint',
    ContentType='application/json',
    Body=json.dumps(data)
)

result = json.loads(response['Body'].read())
print(result)