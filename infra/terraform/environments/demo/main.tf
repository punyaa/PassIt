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
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  # The state bucket is created once by hand in the target account and passed at init:
  #   terraform init -backend-config="bucket=passit-tfstate-<ACCOUNT_ID>"
  # so this environment can be rebuilt in a teammate's account unchanged.
  backend "s3" {
    key          = "demo/terraform.tfstate"
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
      Environment = "demo"
      ManagedBy   = "Terraform"
      Course      = "CS5224"
    }
  }
}

locals {
  # The email feature's on/off switch. Needs both the switch and a sender address.
  notifications_on = var.notifications_enabled && var.notification_sender != null
}

module "network" {
  source = "../../modules/network"

  environment = "demo"
  aws_region  = var.aws_region
  vpc_cidr    = "10.1.0.0/16"
}

module "rds" {
  source = "../../modules/rds"

  environment       = "demo"
  subnet_ids        = module.network.public_subnet_ids
  security_group_id = module.network.rds_security_group_id
}

module "ecs_alb" {
  source = "../../modules/ecs-alb"

  environment                = "demo"
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
    local.notifications_on ? {
      PASSIT_NOTIFICATIONS_BACKEND = "sns"
      PASSIT_EVENTS_TOPIC_ARN      = one(module.notifications[*].topic_arn)
    } : {},
    var.release_image_tag == null ? {} : {
      PASSIT_SCHEDULER_BACKEND  = "eventbridge"
      PASSIT_RELEASE_LAMBDA_ARN = module.release_scheduler.lambda_arn
      PASSIT_SCHEDULER_ROLE_ARN = module.release_scheduler.scheduler_role_arn
    },
  )
}

module "release_scheduler" {
  source = "../../modules/release-scheduler"

  # One schedule group per environment, so demo and staging can share an account.
  group_name = "passit-demo-releases"

  environment       = "demo"
  subnet_ids        = module.network.public_subnet_ids
  security_group_id = module.network.task_security_group_id
  database_url      = module.rds.database_url
  jwt_secret        = module.ecs_alb.jwt_secret
  image_tag         = var.release_image_tag

  # Its result, including the fee.released event, reaches the mailer through the events topic.
  forward_results   = local.notifications_on
  results_topic_arn = one(module.notifications[*].topic_arn)
}

module "monitoring" {
  source = "../../modules/monitoring"

  environment                 = "demo"
  aws_region                  = var.aws_region
  cluster_name                = module.ecs_alb.cluster_name
  api_service_name            = module.ecs_alb.api_service_name
  alb_arn_suffix              = module.ecs_alb.alb_arn_suffix
  api_target_group_arn_suffix = module.ecs_alb.api_target_group_arn_suffix
  rds_instance_id             = module.rds.instance_identifier
  alert_emails                = var.alert_emails
}

module "cdn" {
  source = "../../modules/s3-cloudfront"

  environment  = "demo"
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

# Small JPEG thumbnails of listing photos, made when a photo is uploaded.
module "thumbnailer" {
  source = "../../modules/thumbnailer"

  environment = "demo"
  bucket_name = module.cdn.bucket_name
  bucket_arn  = module.cdn.bucket_arn
  image_tag   = var.thumbnailer_image_tag
}

# Emails for booking and release events. Off until a sender address is given.
module "notifications" {
  source = "../../modules/notifications"
  count  = var.notification_sender == null ? 0 : 1

  environment       = "demo"
  aws_region        = var.aws_region
  sender_address    = var.notification_sender
  copy_to           = var.notification_copy_to
  verify_recipients = var.notification_verify_recipients
  site_url          = "https://${module.cdn.cloudfront_domain}"
  enabled           = var.notifications_enabled
}

# The API publishes booking events to the topic.
resource "aws_iam_role_policy" "task_events" {
  count = var.notification_sender == null ? 0 : 1

  name = "publish-events"
  role = module.ecs_alb.task_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sns:Publish"]
      Resource = one(module.notifications[*].topic_arn)
    }]
  })
}

module "github_oidc" {
  source = "../../modules/github-oidc"

  environment       = "demo"
  aws_region        = var.aws_region
  github_repository = var.github_repository
  subject_prefix    = var.github_oidc_subject_prefix
  # The account has one GitHub OIDC provider. Staging creates it, so demo only looks it up
  # when both share an account; set true when building demo in a different account.
  create_oidc_provider = var.create_github_oidc_provider
  cluster_name         = module.ecs_alb.cluster_name
  ecr_repository_arns = [
    module.ecs_alb.api_repository_arn,
    module.ecs_alb.web_repository_arn,
    module.release_scheduler.repository_arn,
    module.thumbnailer.repository_arn,
  ]
  lambda_function_arns = compact([
    module.release_scheduler.lambda_arn,
    module.thumbnailer.function_arn,
  ])
  task_role_arns = [
    module.ecs_alb.task_role_arn,
    module.ecs_alb.execution_role_arn,
  ]
}
