variable "environment" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "alb_security_group_id" {
  type = string
}

variable "task_security_group_id" {
  type = string
}

variable "database_url_parameter_arn" {
  description = "SSM SecureString holding the SQLAlchemy connection string."
  type        = string
}

variable "api_image_tag" {
  description = "Image tag (git SHA) for the first task definition. CI owns later revisions."
  type        = string
}

variable "web_image_tag" {
  type = string
}

variable "api_desired_count" {
  type    = number
  default = 2
}

variable "web_desired_count" {
  type    = number
  default = 1
}

variable "api_min_capacity" {
  type    = number
  default = 2
}

variable "api_max_capacity" {
  type    = number
  default = 6
}

variable "cookie_secure" {
  description = "Set true once HTTPS (CloudFront) fronts the site, otherwise login cookies are dropped."
  type        = bool
  default     = false
}

variable "fee_hold_minutes" {
  description = "Fee hold after handover. 1 in staging so demos show a real release."
  type        = number
  default     = 1
}

variable "cloudfront_domain" {
  type    = string
  default = null
}

variable "scheduler_group_name" {
  type    = string
  default = "passit-releases"
}

variable "scheduler_role_arns" {
  description = "Roles the API may pass to EventBridge Scheduler."
  type        = list(string)
  default     = []
}

variable "api_environment" {
  description = "Extra non-secret PASSIT_* settings for the API (storage, scheduler, Bedrock)."
  type        = map(string)
  default     = {}
}

variable "api_secrets" {
  description = "Extra secrets for the API: environment variable name to SSM parameter ARN."
  type        = map(string)
  default     = {}
}
