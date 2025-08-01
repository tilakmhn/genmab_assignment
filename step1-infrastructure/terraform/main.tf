terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      Project     = var.project_name
      CreatedBy   = "terraform"
    }
  }
}

# S3 Buckets
resource "aws_s3_bucket" "sagemaker_bucket" {
  bucket = "${var.project_name}-sagemaker-${var.environment}-${random_id.bucket_suffix.hex}"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_versioning" "sagemaker_bucket" {
  bucket = aws_s3_bucket.sagemaker_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# SageMaker Execution Role
resource "aws_iam_role" "sagemaker_execution_role" {
  name = "${var.project_name}-sagemaker-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
      }
    ]
  })
}

# S3 Access Policy
resource "aws_iam_policy" "sagemaker_s3_policy" {
  name = "${var.project_name}-sagemaker-s3-policy-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.sagemaker_bucket.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = aws_s3_bucket.sagemaker_bucket.arn
      }
    ]
  })
}

# SageMaker Policy
resource "aws_iam_policy" "sagemaker_policy" {
  name = "${var.project_name}-sagemaker-policy-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sagemaker:*",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams",
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach policies to role
resource "aws_iam_role_policy_attachment" "sagemaker_s3_attach" {
  role       = aws_iam_role.sagemaker_execution_role.name
  policy_arn = aws_iam_policy.sagemaker_s3_policy.arn
}

resource "aws_iam_role_policy_attachment" "sagemaker_policy_attach" {
  role       = aws_iam_role.sagemaker_execution_role.name
  policy_arn = aws_iam_policy.sagemaker_policy.arn
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "sagemaker_logs" {
  name              = "/aws/sagemaker/${var.project_name}-${var.environment}"
  retention_in_days = 7
}


# ── Lambda execution role ───────────────────────────────────
resource "aws_iam_role" "lambda_exec_role" {
  name = "${var.project_name}-lambda-exec-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Policy: allow SageMaker endpoint ops + CloudWatch logs + S3 read
resource "aws_iam_policy" "lambda_sagemaker_policy" {
  name = "${var.project_name}-lambda-sagemaker-policy-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ─ SageMaker endpoint create / update ─
      {
        Effect   = "Allow"
        Action   = [
          "sagemaker:CreateEndpoint",
          "sagemaker:CreateEndpointConfig",
          "sagemaker:UpdateEndpoint",
          "sagemaker:DescribeEndpoint",
          "sagemaker:DescribeEndpointConfig",
          "sagemaker:DescribeModel"
        ]
        Resource = "*"
      },
      # ─ S3 read (models & code) ─
      {
        Effect   = "Allow"
        Action   = [ "s3:GetObject", "s3:ListBucket" ]
        Resource = [
          aws_s3_bucket.sagemaker_bucket.arn,
          "${aws_s3_bucket.sagemaker_bucket.arn}/*"
        ]
      },
      # ─ CloudWatch logs for Lambda ─
      {
        Effect   = "Allow"
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attach" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_sagemaker_policy.arn
}

# ── Allow pipeline role to invoke & pass Lambda ─────────────
resource "aws_iam_policy" "pipeline_invoke_lambda_policy" {
  name = "${var.project_name}-pipeline-invoke-lambda-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # 1. Invoke the function
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.project_name}-deploy-lambda-${var.environment}"
      },
      # 2. Pass the Lambda-exec role to Lambda service when it is created
      {
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = aws_iam_role.lambda_exec_role.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "pipeline_invoke_lambda_attach" {
  role       = aws_iam_role.sagemaker_execution_role.name
  policy_arn = aws_iam_policy.pipeline_invoke_lambda_policy.arn
}


# ── allow SageMaker to pass its own execution role ──────────
resource "aws_iam_policy" "sagemaker_passrole_policy" {
  name = "${var.project_name}-sagemaker-passrole-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "iam:PassRole"
      Resource = aws_iam_role.sagemaker_execution_role.arn
      Condition = {
        StringEquals = {
          "iam:PassedToService" = "sagemaker.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "sagemaker_passrole_attach" {
  role       = aws_iam_role.sagemaker_execution_role.name
  policy_arn = aws_iam_policy.sagemaker_passrole_policy.arn
}


# -------------------------------------------------------------------
# IAM role that AWS Lambda can assume
# -------------------------------------------------------------------
resource "aws_iam_role" "lambda_bedrock_exec" {
  name = "lambda-bedrock-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = { Service = "lambda.amazonaws.com" },
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_bedrock_exec_policy" {
  name = "lambda-bedrock-exec-policy"
  role = aws_iam_role.lambda_bedrock_exec.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      # ── CloudWatch Logs ────────────────────────────────────────────
      {
        Sid      = "AllowWritingLogs",
        Effect   = "Allow",
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:*:*:*"
      },

      # ── Amazon Bedrock (text models) ───────────────────────────────
      {
        Sid      = "AllowBedrockInvoke",
        Effect   = "Allow",
        Action   = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ],

        Resource = "arn:aws:bedrock:*:*:foundation-model/*"

       
      }
    ]
  })
}



# Needed to resolve account id variable
data "aws_caller_identity" "current" {}