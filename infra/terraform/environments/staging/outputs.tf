output "vpc_id" {
  value = module.network.vpc_id
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}

output "task_security_group_id" {
  value = module.network.task_security_group_id
}

output "rds_endpoint" {
  value = module.rds.endpoint
}

output "database_url_parameter_name" {
  value = module.rds.database_url_parameter_name
}

output "alb_dns_name" {
  value = module.ecs_alb.alb_dns_name
}

output "cluster_name" {
  value = module.ecs_alb.cluster_name
}

output "api_repository_url" {
  value = module.ecs_alb.api_repository_url
}

output "web_repository_url" {
  value = module.ecs_alb.web_repository_url
}

output "migrate_task_definition" {
  value = module.ecs_alb.migrate_task_definition
}

output "cloudfront_domain" {
  value = module.cdn.cloudfront_domain
}

output "media_bucket" {
  value = module.cdn.bucket_name
}

output "github_deploy_role_arn" {
  description = "Set as the AWS_DEPLOY_ROLE_ARN repository variable in GitHub."
  value       = module.github_oidc.role_arn
}

output "release_repository_url" {
  value = module.release_scheduler.repository_url
}

output "dashboard_name" {
  value = module.monitoring.dashboard_name
}
