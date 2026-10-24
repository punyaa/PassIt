output "repository_url" {
  value = aws_ecr_repository.release.repository_url
}

output "group_name" {
  value = aws_scheduler_schedule_group.releases.name
}

output "scheduler_role_arn" {
  value = aws_iam_role.scheduler.arn
}

output "lambda_arn" {
  description = "Null until the image tag is set."
  value       = try(aws_lambda_function.release[0].arn, null)
}

output "lambda_function_name" {
  value = try(aws_lambda_function.release[0].function_name, null)
}

output "repository_arn" {
  value = aws_ecr_repository.release.arn
}
