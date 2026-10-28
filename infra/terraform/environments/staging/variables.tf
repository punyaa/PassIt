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

variable "github_oidc_subject_prefix" {
  description = "How GitHub names this repository in its OIDC token (the immutable owner and repository IDs form). Null uses the name-based form."
  type        = string
  default     = "repo:punyaa@30744939/PassIt@1421865475"
}
