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

variable "web_service_name" {
  type = string
}

variable "rds_instance_id" {
  type = string
}

variable "api_min_capacity" {
  type    = number
  default = 2
}

variable "api_max_capacity" {
  type    = number
  default = 6
}

variable "web_desired_count" {
  type    = number
  default = 1
}

variable "start_days" {
  description = "EventBridge day-of-week field for the morning start: * for daily, MON-FRI for weekdays."
  type        = string
  default     = "*"
}
