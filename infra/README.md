# PassIt infrastructure

The Platform stream owns this directory, the Dockerfiles, `compose.yaml`, CI/CD, authentication infrastructure, monitoring and cost controls.

## Environments

- `terraform/environments/staging/`: integration, 1-minute fee hold, automated tests and evaluation runs.
- `terraform/environments/demo/`: stable evaluator-facing environment. Seeded, then left alone.

Both target `ap-southeast-1`. Do not create production resources for the four-week prototype.

## Modules

| Module | What it creates |
| --- | --- |
| `network` | VPC, two public subnets, three chained security groups, free S3 gateway endpoint. No NAT Gateway. |
| `rds` | PostgreSQL 16, single-AZ, private. Writes the connection string to SSM. |
| `ecs-alb` | ECR, Fargate (ARM64) API and web services, ALB, JWT secret, autoscaling (2 to 6), one-off migration task. |
| `s3-cloudfront` | Private media bucket and the CloudFront distribution that fronts the whole site. |
| `release-scheduler` | EventBridge schedule group, fee-release Lambda (container image), roles. |
| `monitoring` | Alarms, dashboard, USD 35 monthly budget, alert topic. |
| `github-oidc` | Deploy role GitHub Actions assumes through OIDC. No stored AWS keys. |

## Bootstrap (once per AWS account)

```bash
aws s3api create-bucket --bucket passit-tfstate-<ACCOUNT_ID> --region ap-southeast-1 \
  --create-bucket-configuration LocationConstraint=ap-southeast-1
aws s3api put-bucket-versioning --bucket passit-tfstate-<ACCOUNT_ID> --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket passit-tfstate-<ACCOUNT_ID> \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket passit-tfstate-<ACCOUNT_ID> \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

Terraform locks state natively in S3 (`use_lockfile`), so no DynamoDB table is needed.

## Build an environment from nothing (about an hour)

```bash
cd infra/terraform/environments/demo          # or staging
terraform init -backend-config="bucket=passit-tfstate-<ACCOUNT_ID>"   # staging has the bucket baked in

# 1. Registries first, so images exist before the services start.
terraform apply -var api_image_tag=<TAG> -var web_image_tag=<TAG> \
  -target=module.ecs_alb.aws_ecr_repository.api -target=module.ecs_alb.aws_ecr_repository.web \
  -target=module.release_scheduler.aws_ecr_repository.release

# 2. Build and push (Fargate runs ARM64).
REG=<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com
aws ecr get-login-password | docker login --username AWS --password-stdin $REG
docker build --platform linux/arm64 -t $REG/passit-<env>-api:<TAG> api && docker push $REG/passit-<env>-api:<TAG>
docker build --platform linux/arm64 --build-arg NEXT_PUBLIC_API_URL=/v1 -t $REG/passit-<env>-web:<TAG> web && docker push $REG/passit-<env>-web:<TAG>
docker build --platform linux/arm64 --provenance=false -f api/Dockerfile.lambda -t $REG/passit-<env>-release:<TAG> api && docker push $REG/passit-<env>-release:<TAG>

# 3. Everything else, including the release Lambda.
terraform apply -var api_image_tag=<TAG> -var web_image_tag=<TAG> -var release_image_tag=<TAG> \
  -var 'alert_emails=["you@u.nus.edu"]'

# 4. Migrate and seed (also the demo reset).
AWS_PROFILE=<profile> scripts/demo-reset/reset.sh <env>
```

Building `demo` in the same account as `staging`: leave `create_github_oidc_provider` false (the account has one provider). In a different account, set it true.

## Day-to-day

- CI (`.github/workflows/deploy-staging.yml`) builds, migrates and deploys the API, web app and fee-release Lambda on every merge to `main`. It assumes the staging deploy role through OIDC with no setup. Set the repository variable `AWS_DEPLOY_ROLE_ARN` only to deploy to a different AWS account.
- Terraform ignores task-definition changes on the ECS services and the image of the fee-release Lambda, because CI owns them. After a `terraform apply` that replaces a task definition, re-register it with the current image and run `aws ecs update-service`.
- Watch a deploy: ECS, cluster, service, Deployments tab. Logs: CloudWatch `/ecs/passit-<env>-api`. Dashboard: `passit-<env>`.

## Known limits

- Cost allocation tags cannot be activated from a linked account; the organisation's management account must do it.
- Media is served through CloudFront without signed URLs, so evidence photos are reachable by anyone holding the (unguessable) key. See the TODO in `api/app/integrations/storage.py`.
- Single-AZ database, no NAT Gateway, HTTP between CloudFront and the ALB: acceptable for the prototype, not for production.
