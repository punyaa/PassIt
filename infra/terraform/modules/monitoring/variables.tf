variable "environment" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "api_service_name" {
  type = string
}

variable "alb_arn_suffix" {
  type = string
}

variable "api_target_group_arn_suffix" {
  type = string
}

variable "rds_instance_id" {
  type = string
}

variable "alert_emails" {
  description = "Team addresses for alarms and budget alerts. Empty skips the subscriptions and the budget."
  type        = list(string)
  default     = []
}

variable "monthly_budget_usd" {
  type    = number
  default = 35
}
