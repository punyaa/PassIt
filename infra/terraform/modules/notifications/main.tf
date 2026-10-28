# Emails for booking and fee-release events.
#
#   API or release Lambda -> SNS topic -> mailer Lambda -> Amazon SES -> inbox
#
# The API publishes booking events straight to the topic. The fee-release Lambda sits in the
# VPC with no route to SNS, so its result is forwarded to the topic by a Lambda destination
# (see the release-scheduler module). The mailer is a plain Python function with no
# dependencies, so Terraform zips and deploys it itself.
#
# SES starts in sandbox mode: it delivers only to verified addresses. This module creates an
# identity for each address it is given, and AWS emails each one a verification link that has
# to be clicked once. Production access, which lifts the restriction, is a request to AWS.

data "aws_caller_identity" "current" {}

locals {
  name = "passit-${var.environment}"
  # Every address SES must know: the sender, the team copy, and anyone else to verify.
  addresses = distinct(concat([var.sender_address], var.copy_to, var.verify_recipients))
}

resource "aws_sns_topic" "events" {
  name = "${local.name}-events"
}

resource "aws_sesv2_email_identity" "address" {
  for_each = toset(local.addresses)

  email_identity = each.value
}

data "archive_file" "mailer" {
  type        = "zip"
  source_dir  = "${path.module}/../../../lambdas/mailer"
  output_path = "${path.module}/.build/mailer.zip"
  excludes    = ["__pycache__", "*.pyc"]
}

resource "aws_cloudwatch_log_group" "mailer" {
  name              = "/aws/lambda/${local.name}-mailer"
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

resource "aws_iam_role" "mailer" {
  name               = "${local.name}-mailer"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.mailer.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# May send only as the verified sender.
resource "aws_iam_role_policy" "send" {
  name = "send-as-sender"
  role = aws_iam_role.mailer.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ses:SendEmail"]
      Resource = "arn:aws:ses:${var.aws_region}:${data.aws_caller_identity.current.account_id}:identity/${var.sender_address}"
    }]
  })
}

resource "aws_lambda_function" "mailer" {
  function_name    = "${local.name}-mailer"
  role             = aws_iam_role.mailer.arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "handler.handler"
  filename         = data.archive_file.mailer.output_path
  source_code_hash = data.archive_file.mailer.output_base64sha256
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      SEND_EMAILS = tostring(var.enabled)
      SENDER      = "PassIt <${var.sender_address}>"
      COPY_TO     = join(",", var.copy_to)
      SITE_URL    = var.site_url
    }
  }

  depends_on = [aws_cloudwatch_log_group.mailer, aws_iam_role_policy_attachment.logs]
}

resource "aws_lambda_permission" "from_sns" {
  statement_id  = "AllowSnsInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mailer.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.events.arn
}

resource "aws_sns_topic_subscription" "mailer" {
  topic_arn = aws_sns_topic.events.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.mailer.arn

  depends_on = [aws_lambda_permission.from_sns]
}
