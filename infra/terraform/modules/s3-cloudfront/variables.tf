variable "environment" {
  type = string
}

variable "alb_dns_name" {
  description = "Origin for the API and the web app."
  type        = string
}

variable "extra_cors_origins" {
  description = "Additional origins allowed to PUT to the bucket, e.g. http://localhost:3000 for local development."
  type        = list(string)
  default     = []
}
