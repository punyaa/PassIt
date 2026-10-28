output "topic_arn" {
  description = "Publish booking and release events here."
  value       = aws_sns_topic.events.arn
}

output "mailer_function_name" {
  value = aws_lambda_function.mailer.function_name
}

output "verified_addresses" {
  description = "Addresses SES was asked to verify. Each must click the link AWS emails it."
  value       = local.addresses
}
