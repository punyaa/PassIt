variable "environment" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "github_repository" {
  description = "owner/name of the repository allowed to deploy."
  type        = string
}

variable "branch" {
  type    = string
  default = "main"
}

variable "create_oidc_provider" {
  description = "There is one GitHub OIDC provider per account. Set false if another stack already created it."
  type        = bool
  default     = true
}

variable "cluster_name" {
  type = string
}

variable "ecr_repository_arns" {
  type = list(string)
}

variable "task_role_arns" {
  description = "ECS execution and task roles the deploy role may pass to new task definitions."
  type        = list(string)
}

variable "lambda_function_arns" {
  description = "Functions the deploy role may update with a new image (the fee-release Lambda)."
  type        = list(string)
  default     = []
}

variable "subject_prefix" {
  description = "Prefix of the token's sub claim. Check the repository with `gh api repos/<owner>/<repo>/actions/oidc/customization/sub`: when use_immutable_subject is true, use its sub_claim_prefix. Null falls back to the older repo:<owner>/<repo> form."
  type        = string
  default     = null
}