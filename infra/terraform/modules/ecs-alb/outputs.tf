output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "api_service_name" {
  value = aws_ecs_service.api.name
}

output "web_service_name" {
  value = aws_ecs_service.web.name
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "alb_arn_suffix" {
  value = aws_lb.main.arn_suffix
}

output "api_target_group_arn_suffix" {
  value = aws_lb_target_group.api.arn_suffix
}

output "api_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "web_repository_url" {
  value = aws_ecr_repository.web.repository_url
}

output "task_role_name" {
  value = aws_iam_role.task.name
}

output "execution_role_name" {
  value = aws_iam_role.execution.name
}

output "api_log_group_name" {
  value = aws_cloudwatch_log_group.api.name
}

output "migrate_task_definition" {
  value = aws_ecs_task_definition.migrate.family
}

output "task_role_arn" {
  value = aws_iam_role.task.arn
}

output "execution_role_arn" {
  value = aws_iam_role.execution.arn
}

output "api_repository_arn" {
  value = aws_ecr_repository.api.arn
}

output "web_repository_arn" {
  value = aws_ecr_repository.web.arn
}

output "jwt_secret_parameter_name" {
  value = aws_ssm_parameter.jwt_secret.name
}

output "jwt_secret" {
  value     = random_password.jwt.result
  sensitive = true
}
