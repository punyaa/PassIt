terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0, < 7.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # State bucket is created once by hand (see infra/README.md, "Bootstrap").
  # use_lockfile gives native S3 locking, so no DynamoDB table is needed.
  backend "s3" {
    bucket       = "passit-tfstate-034313912472"
    key          = "staging/terraform.tfstate"
    region       = "ap-southeast-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = {
      Project     = "PassIt"
      Environment = "staging"
      ManagedBy   = "Terraform"
      Course      = "CS5224"
    }
  }
}

module "network" {
  source = "../../modules/network"

  environment = "staging"
  aws_region  = var.aws_region
  vpc_cidr    = "10.0.0.0/16"
}

module "rds" {
  source = "../../modules/rds"

  environment       = "staging"
  subnet_ids        = module.network.public_subnet_ids
  security_group_id = module.network.rds_security_group_id
}

module "ecs_alb" {
  source = "../../modules/ecs-alb"

  environment                = "staging"
  aws_region                 = var.aws_region
  vpc_id                     = module.network.vpc_id
  subnet_ids                 = module.network.public_subnet_ids
  alb_security_group_id      = module.network.alb_security_group_id
  task_security_group_id     = module.network.task_security_group_id
  database_url_parameter_arn = module.rds.database_url_parameter_arn
  api_image_tag              = var.api_image_tag
  web_image_tag              = var.web_image_tag

  # CloudFront terminates HTTPS, so login cookies can be Secure.
  cloudfront_domain = module.cdn.cloudfront_domain
  cookie_secure     = true

  # The API only switches to EventBridge once the release Lambda image exists. The in-process
  # sweep stays on as an idempotent safety net either way.
  scheduler_group_name = module.release_scheduler.group_name
  scheduler_role_arns  = [module.release_scheduler.scheduler_role_arn]

  api_environment = merge(
    {
      PASSIT_STORAGE_BACKEND   = "s3"
      PASSIT_S3_BUCKET         = module.cdn.bucket_name
      PASSIT_S3_PREFIX         = "media/"
      PASSIT_CLOUDFRONT_DOMAIN = module.cdn.cloudfront_domain
    },
    var.release_image_tag == null ? {} : {
      PASSIT_SCHEDULER_BACKEND  = "eventbridge"
      PASSIT_RELEASE_LAMBDA_ARN = module.release_scheduler.lambda_arn
      PASSIT_SCHEDULER_ROLE_ARN = module.release_scheduler.scheduler_role_arn
    },
  )
}

module "release_scheduler" {
  source = "../../modules/release-scheduler"

  environment       = "staging"
  subnet_ids        = module.network.public_subnet_ids
  security_group_id = module.network.task_security_group_id
  database_url      = module.rds.database_url
  jwt_secret        = module.ecs_alb.jwt_secret
  image_tag         = var.release_image_tag
}

module "monitoring" {
  source = "../../modules/monitoring"

  environment                 = "staging"
  aws_region                  = var.aws_region
  cluster_name                = module.ecs_alb.cluster_name
  api_service_name            = module.ecs_alb.api_service_name
  alb_arn_suffix              = module.ecs_alb.alb_arn_suffix
  api_target_group_arn_suffix = module.ecs_alb.api_target_group_arn_suffix
  rds_instance_id             = module.rds.instance_identifier
  alert_emails                = var.alert_emails
}

# Off by default: while staging is down, ALB health checks fail and CI deploys have nothing
# to roll onto. Switch on with -var enable_nightly_shutdown=true to save credits.
module "nightly_shutdown" {
  source = "../../modules/nightly-shutdown"
  count  = var.enable_nightly_shutdown ? 1 : 0

  environment      = "staging"
  aws_region       = var.aws_region
  cluster_name     = module.ecs_alb.cluster_name
  api_service_name = module.ecs_alb.api_service_name
  web_service_name = module.ecs_alb.web_service_name
  rds_instance_id  = module.rds.instance_identifier
  start_days       = var.start_days
}

module "cdn" {
  source = "../../modules/s3-cloudfront"

  environment  = "staging"
  alb_dns_name = module.ecs_alb.alb_dns_name
}

# The API presigns uploads and reads evidence, so its task role needs the media prefix only.
resource "aws_iam_role_policy" "task_media" {
  name = "media-bucket"
  role = module.ecs_alb.task_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:GetObject"]
      Resource = "${module.cdn.bucket_arn}/media/*"
    }]
  })
}

module "github_oidc" {
  source = "../../modules/github-oidc"

  environment       = "staging"
  aws_region        = var.aws_region
  github_repository = var.github_repository
  cluster_name      = module.ecs_alb.cluster_name
  ecr_repository_arns = [
    module.ecs_alb.api_repository_arn,
    module.ecs_alb.web_repository_arn,
  ]
  task_role_arns = [
    module.ecs_alb.task_role_arn,
    module.ecs_alb.execution_role_arn,
  ]
}
