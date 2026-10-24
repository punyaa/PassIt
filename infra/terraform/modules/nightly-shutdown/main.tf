# Credit saver: staging runs 09:00 to 21:00 Singapore time. Most of the bill is hourly, so
# this cuts it by roughly half. A stopped RDS instance restarts itself after 7 days, so the
# morning start rule matters even if nobody uses staging.
#
# While it is down, ALB health checks fail and deploys have nothing to roll onto.

locals {
  name = "passit-${var.environment}"
  tz   = "Asia/Singapore"
}

data "aws_caller_identity" "current" {}

# The API's task count belongs to Application Auto Scaling, so shut it down through the
# scaling bounds. Setting only the desired count would be undone within a minute.
resource "aws_appautoscaling_scheduled_action" "api_down" {
  name               = "${local.name}-api-down"
  service_namespace  = "ecs"
  resource_id        = "service/${var.cluster_name}/${var.api_service_name}"
  scalable_dimension = "ecs:service:DesiredCount"
  schedule           = "cron(0 21 * * ? *)"
  timezone           = local.tz

  scalable_target_action {
    min_capacity = 0
    max_capacity = 0
  }
}

resource "aws_appautoscaling_scheduled_action" "api_up" {
  name               = "${local.name}-api-up"
  service_namespace  = "ecs"
  resource_id        = "service/${var.cluster_name}/${var.api_service_name}"
  scalable_dimension = "ecs:service:DesiredCount"
  schedule           = "cron(0 9 ? * ${var.start_days} *)"
  timezone           = local.tz

  scalable_target_action {
    min_capacity = var.api_min_capacity
    max_capacity = var.api_max_capacity
  }
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
  name               = "${local.name}-nightly-shutdown"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

resource "aws_iam_role_policy" "scheduler" {
  name = "start-stop"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecs:UpdateService"]
        Resource = "arn:aws:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:service/${var.cluster_name}/${var.web_service_name}"
      },
      {
        Effect   = "Allow"
        Action   = ["rds:StartDBInstance", "rds:StopDBInstance"]
        Resource = "arn:aws:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:db:${var.rds_instance_id}"
      },
    ]
  })
}

resource "aws_scheduler_schedule" "web_down" {
  name                         = "${local.name}-web-down"
  schedule_expression          = "cron(0 21 * * ? *)"
  schedule_expression_timezone = local.tz

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ecs:updateService"
    role_arn = aws_iam_role.scheduler.arn
    input = jsonencode({
      Cluster      = var.cluster_name
      Service      = var.web_service_name
      DesiredCount = 0
    })
  }
}

resource "aws_scheduler_schedule" "web_up" {
  name                         = "${local.name}-web-up"
  schedule_expression          = "cron(0 9 ? * ${var.start_days} *)"
  schedule_expression_timezone = local.tz

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ecs:updateService"
    role_arn = aws_iam_role.scheduler.arn
    input = jsonencode({
      Cluster      = var.cluster_name
      Service      = var.web_service_name
      DesiredCount = var.web_desired_count
    })
  }
}

resource "aws_scheduler_schedule" "rds_stop" {
  name                         = "${local.name}-rds-stop"
  schedule_expression          = "cron(5 21 * * ? *)"
  schedule_expression_timezone = local.tz

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:rds:stopDBInstance"
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ DbInstanceIdentifier = var.rds_instance_id })
  }
}

# Ten minutes ahead of the tasks so the database is ready when they start.
resource "aws_scheduler_schedule" "rds_start" {
  name                         = "${local.name}-rds-start"
  schedule_expression          = "cron(50 8 ? * ${var.start_days} *)"
  schedule_expression_timezone = local.tz

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:rds:startDBInstance"
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ DbInstanceIdentifier = var.rds_instance_id })
  }
}
