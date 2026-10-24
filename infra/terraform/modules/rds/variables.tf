variable "environment" {
  description = "Environment name used in resource names (staging or demo)."
  type        = string
}

variable "subnet_ids" {
  description = "Subnets in at least two availability zones for the DB subnet group."
  type        = list(string)
}

variable "security_group_id" {
  description = "rds-sg, which admits 5432 from task-sg only."
  type        = string
}

variable "instance_class" {
  type    = string
  default = "db.t4g.micro"
}
