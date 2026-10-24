variable "aws_region" {
  description = "AWS region fixed by the prototype plan."
  type        = string
  default     = "ap-southeast-1"
}

variable "aws_profile" {
  description = "AWS CLI profile (IAM Identity Center). Null in CI, which uses OIDC credentials."
  type        = string
  default     = null
}

variable "api_image_tag" {
  description = "API image tag (git SHA) pushed to ECR."
  type        = string
}

variable "web_image_tag" {
  description = "Web image tag (git SHA) pushed to ECR."
  type        = string
}

variable "github_repository" {
  description = "owner/name of the repository whose main branch may deploy."
  type        = string
  default     = "punyaa/PassIt"
}

variable "release_image_tag" {
  description = "Release Lambda image tag in ECR. Null until the image has been pushed."
  type        = string
  default     = null
}

variable "alert_emails" {
  description = "Team addresses for CloudWatch alarms and the USD 35 budget. Empty skips both."
  type        = list(string)
  default     = []
}

variable "start_days" {
  description = "Day-of-week field for the morning start of demo: * daily, MON-FRI weekdays."
  type        = string
  default     = "*"
}

variable "enable_nightly_shutdown" {
  description = "Stop demo 21:00 to 09:00 SGT to save credits. Off so evaluators can always reach it."
  type        = bool
  default     = false
}

variable "create_github_oidc_provider" {
  description = "False when staging in the same account already created the GitHub OIDC provider."
  type        = bool
  default     = false
}
