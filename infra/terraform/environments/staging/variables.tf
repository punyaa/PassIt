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

variable "thumbnailer_image_tag" {
  description = "Thumbnailer Lambda image tag in ECR. Null until the first image has been pushed."
  type        = string
  default     = null
}

variable "notification_sender" {
  description = "Address booking and release emails come from. Null turns the email feature off. SES sends it a verification link."
  type        = string
  default     = null
}

variable "notification_copy_to" {
  description = "Addresses that receive a Bcc of every email, for example the team."
  type        = list(string)
  default     = []
}

variable "notification_verify_recipients" {
  description = "More addresses to verify so they can receive email while SES is in sandbox mode."
  type        = list(string)
  default     = []
}

variable "notifications_enabled" {
  description = "Switch for booking and release emails. False (the default) sends nothing: the API stops publishing events and the mailer ignores any that arrive. Needs notification_sender too, and that must be an address on a domain you control with DKIM set up; a university or free-mail address is rejected by receivers that enforce DMARC."
  type        = bool
  default     = false
}