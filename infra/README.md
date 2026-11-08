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
| `thumbnailer` | ECR repository, role, and the Lambda (container image) that S3 calls for each new listing photo, plus the bucket notification that triggers it |
| `notifications` | SNS events topic, the mailer Lambda (zipped by Terraform), SES email identities, the permissions between them |
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

# 3. Everything else, including the release Lambda. Add the thumbnailer image the same way:
#    docker build --platform linux/arm64 --provenance=false -t $REG/passit-<env>-thumbnailer:<TAG> infra/lambdas/thumbnailer
terraform apply -var api_image_tag=<TAG> -var web_image_tag=<TAG> -var release_image_tag=<TAG> \
  -var thumbnailer_image_tag=<TAG> -var 'alert_emails=["you@u.nus.edu"]' \
  -var notification_sender=you@u.nus.edu -var 'notification_copy_to=["you@u.nus.edu"]'

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
- Media is served through CloudFront without signed URLs until a CloudFront key pair is provisioned and `PASSIT_CLOUDFRONT_KEY_PAIR_ID` / `PASSIT_CLOUDFRONT_PRIVATE_KEY` are set, so evidence photos are reachable by anyone holding the (unguessable) key. The API already signs when configured (see `api/app/integrations/storage.py`).
- Single-AZ database, no NAT Gateway, HTTP between CloudFront and the ALB: acceptable for the prototype, not for production.

## Photo thumbnails and email events

Both are built on events, so neither adds work to a request.

- **Thumbnails.** Uploading a listing photo makes S3 call the `thumbnailer` Lambda, which writes a small JPEG under `thumbs/` in the same bucket. CloudFront serves `/thumbs/*` like `/media/*`. Set `thumbnailer_image_tag` once the first image is pushed; after that CI updates the function on every deploy. To thumbnail photos uploaded earlier, run `scripts/thumbnails/backfill.sh <env>`.
- **Email events.** The API publishes a JSON event to the `passit-<env>-events` SNS topic after each booking step, and the `mailer` Lambda turns it into emails through SES. The fee-release Lambda cannot reach SNS from inside the VPC, so Lambda forwards its result to the same topic (a success destination) and the mailer picks the event out of it.
- **The on/off switch.** `notifications_enabled` (default `false`) controls the whole feature. Off: the API publishes nothing, the release Lambda forwards nothing, and the mailer ignores anything that arrives (it sends only when its `SEND_EMAILS` setting is exactly `true`). The topic, mailer and SES identity stay deployed, so turning it on is a one-line change: `terraform apply -var notifications_enabled=true`. It also needs `notification_sender`.
- **The sender address matters.** Receivers check that a message really comes from the domain in its From line. A university address such as `u.nus.edu` publishes `p=reject` and only authorises its own mail servers, so mail sent "from" it through SES is refused (SES forwards the bounce notice to that inbox). Use an address on a domain you own, verified in SES with DKIM; a free-mail address is no better. Until you have one, leave `notifications_enabled` off.
- **SES sandbox.** A new SES account can only send to verified addresses. Terraform creates an identity for the sender, for `notification_copy_to` (a Bcc of every email) and for `notification_verify_recipients`; AWS emails each a link that must be clicked once. Seed and example addresses (`passit.demo`, `example.com`) are never emailed. To email anyone, request SES production access from AWS.
- **Keeping your addresses out of git.** Put personal values in `environments/<env>/terraform.auto.tfvars`, which is gitignored and read automatically.
