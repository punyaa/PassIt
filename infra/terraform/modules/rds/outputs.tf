output "endpoint" {
  value = aws_db_instance.main.address
}

output "instance_identifier" {
  value = aws_db_instance.main.identifier
}

output "database_url_parameter_name" {
  value = aws_ssm_parameter.database_url.name
}

output "database_url_parameter_arn" {
  value = aws_ssm_parameter.database_url.arn
}

output "database_url" {
  value     = aws_ssm_parameter.database_url.value
  sensitive = true
}
