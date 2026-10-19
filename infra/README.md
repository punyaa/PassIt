# PassIt infrastructure

P1 Platform owns this directory, the Dockerfiles, `compose.yaml`, CI/CD, authentication infrastructure, monitoring and cost controls.

## Environments

- `terraform/environments/staging/` — integration, shortened hold timers and automated tests.
- `terraform/environments/demo/` — stable evaluator-facing environment.

Both environments target `ap-southeast-1`. Do not create production resources for the four-week prototype.

## Planned modules

- `network` — VPC, public ECS subnets, routing and the free S3 gateway endpoint.
- `ecs-alb` — ECR, two Fargate tasks, ALB, health checks and autoscaling.
- `rds` — PostgreSQL 16, single-AZ for the prototype.
- `s3-cloudfront` — listing and condition evidence storage and delivery.
- `eventbridge` — one-off fee-release schedules and Lambda target.
- `monitoring` — CloudWatch logs, alarms, budget and cost tags.

The checked-in Terraform currently freezes environment inputs and module boundaries only. Resource creation should arrive through reviewed P1 pull requests with a plan output, estimated cost and teardown instructions.
