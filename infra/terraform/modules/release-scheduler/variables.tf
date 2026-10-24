variable "environment" {
  type = string
}

variable "group_name" {
  type    = string
  default = "passit-releases"
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_id" {
  description = "task-sg: already allowed to reach RDS on 5432."
  type        = string
}

variable "database_url" {
  description = "SQLAlchemy connection string. Passed as a value, not read from SSM, so a fresh environment plans before the parameter exists."
  type        = string
  sensitive   = true
}

variable "image_tag" {
  description = "Release Lambda image tag in ECR. Null creates only the repository, schedule group and roles, so the image can be pushed first."
  type        = string
  default     = null
}

variable "jwt_secret" {
  description = "The environment's JWT secret (settings refuse to load without a real one outside development)."
  type        = string
  sensitive   = true
}
