# Fee-release plumbing. The API creates one one-off schedule per handover; each schedule
# invokes this Lambda once. The handler is written by B2 and is idempotent.
#
# The Lambda sits in the VPC so it can reach RDS. The prototype has no NAT Gateway, so it
# cannot reach SSM or the internet; the database URL is injected as an environment variable.

data "aws_caller_identity" "current" {}

locals {
  name = "passit-${var.environment}"
}

resource "aws_ecr_repository" "release" {
  name                 = "${local.name}-release"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_scheduler_schedule_group" "releases" {
  name = var.group_name
}

resource "aws_cloudwatch_log_group" "release" {
  name              = "/aws/lambda/${local.name}-release"
  retention_in_days = 7
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.name}-release-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

# Logs plus the network interfaces a VPC Lambda needs.
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# The release handler never signs or checks a session, but the app's settings refuse to load
# with the default secret outside development, so the Lambda needs the real one.
resource "aws_lambda_function" "release" {
  count = var.image_tag == null ? 0 : 1

  function_name = "${local.name}-release"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.release.repository_url}:${var.image_tag}"
  architectures = ["arm64"]
  timeout       = 60
  memory_size   = 512

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.security_group_id]
  }

  environment {
    variables = {
      PASSIT_ENVIRONMENT  = var.environment
      PASSIT_DATABASE_URL = var.database_url
      PASSIT_JWT_SECRET   = var.jwt_secret
    }
  }

  depends_on = [aws_cloudwatch_log_group.release, aws_iam_role_policy_attachment.lambda_vpc]
}

data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.name}-scheduler-invoke"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

resource "aws_iam_role_policy" "scheduler_invoke" {
  count = var.image_tag == null ? 0 : 1

  name = "invoke-release-lambda"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = aws_lambda_function.release[0].arn
    }]
  })
}
