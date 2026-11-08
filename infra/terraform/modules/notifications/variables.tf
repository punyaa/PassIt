variable "environment" {
  type = string
}

variable "sender_address" {
  description = "The email address messages come from. SES sends it a verification link."
  type        = string
}

variable "copy_to" {
  description = "Addresses that receive a Bcc of every email, for example the team. Each is verified in SES."
  type        = list(string)
  default     = []
}

variable "verify_recipients" {
  description = "Further addresses to verify while SES is in sandbox mode, so they can receive emails."
  type        = list(string)
  default     = []
}

variable "site_url" {
  description = "The site's address, for the link in each email, e.g. https://d123.cloudfront.net"
  type        = string
}

variable "aws_region" {
  type = string
}

variable "enabled" {
  description = "Send emails. False leaves everything deployed but the mailer ignores events, so the feature can be switched on and off without recreating anything."
  type        = bool
  default     = false
}