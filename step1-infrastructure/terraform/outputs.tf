output "sagemaker_role_arn" {
  value = aws_iam_role.sagemaker_execution_role.arn
}

output "s3_bucket_name" {
  value = aws_s3_bucket.sagemaker_bucket.bucket
}

output "lambda_exec_role_arn" {
  value = aws_iam_role.lambda_exec_role.arn
}

output "lambda_bedrock_exec_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_bedrock_exec.arn
}