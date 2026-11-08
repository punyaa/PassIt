output "repository_url" {
  value = aws_ecr_repository.thumbnailer.repository_url
}

output "repository_arn" {
  value = aws_ecr_repository.thumbnailer.arn
}

output "function_name" {
  description = "Null until the image tag is set."
  value       = try(aws_lambda_function.thumbnailer[0].function_name, null)
}

output "function_arn" {
  description = "Null until the image tag is set."
  value       = try(aws_lambda_function.thumbnailer[0].arn, null)
}
