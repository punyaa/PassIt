variable "environment" {
  description = "Environment name used in resource names (staging or demo)."
  type        = string
}

variable "aws_region" {
  description = "Region for the S3 gateway endpoint service name."
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR. Subnets are carved out as /24 blocks."
  type        = string
  default     = "10.0.0.0/16"
}
