#!/usr/bin/env bash
# Reset a PassIt cloud environment to the seeded demo state, from your laptop.
#
#   AWS_PROFILE=nus-sso scripts/demo-reset/reset.sh demo
#   AWS_PROFILE=nus-sso scripts/demo-reset/reset.sh staging
#
# Runs a one-off ECS task inside the VPC (the database is private): it migrates, truncates
# every PassIt table, and re-runs the seed (22 users, 43 listings, 17 bookings). Target: under
# five minutes, then confirms the site is healthy and serving listings.
set -euo pipefail

ENV_NAME="${1:-}"
case "$ENV_NAME" in
  staging | demo) ;;
  *) echo "usage: $0 staging|demo" >&2; exit 2 ;;
esac

export AWS_REGION="${AWS_REGION:-ap-southeast-1}" AWS_PAGER=""
CLUSTER="passit-$ENV_NAME"
START=$(date +%s)

echo "Resetting $ENV_NAME ($CLUSTER). This deletes all data in that database."
if [ "${ASSUME_YES:-}" != "1" ]; then
  read -r -p "Type the environment name to continue: " answer
  [ "$answer" = "$ENV_NAME" ] || { echo "Aborted."; exit 1; }
fi

network=$(aws ecs describe-services --cluster "$CLUSTER" --services api \
  --query 'services[0].networkConfiguration' --output json)
task=$(aws ecs run-task --cluster "$CLUSTER" --task-definition "$CLUSTER-migrate" \
  --launch-type FARGATE --network-configuration "$network" \
  --overrides '{"containerOverrides":[{"name":"migrate","command":["sh","-c","alembic upgrade head && python -m scripts.seed --reset"]}]}' \
  --query 'tasks[0].taskArn' --output text)
echo "Seed task: ${task##*/}"
aws ecs wait tasks-stopped --cluster "$CLUSTER" --tasks "$task"

code=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$task" \
  --query 'tasks[0].containers[0].exitCode' --output text)
stream="migrate/migrate/${task##*/}"
# Show the summary lines only: the seed also prints session tokens, which stay in CloudWatch.
aws logs get-log-events --log-group-name "/ecs/$CLUSTER-api" --log-stream-name "$stream" \
  --query 'events[].message' --output text | tr '\t' '\n' | grep -E "^(Seeded|Demo logins)" || true
[ "$code" = "0" ] || { echo "Seed task failed (exit $code). Log stream: $stream"; exit 1; }

domain=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Comment=='PassIt $ENV_NAME'].DomainName | [0]" --output text)
health=$(curl -fsS -m 15 "https://$domain/health")
listings=$(curl -fsS -m 15 "https://$domain/v1/listings?limit=50" | python3 -c 'import sys,json;print(len(json.load(sys.stdin)))')
echo "Health: $health"
echo "Listings visible: $listings"
echo "Reset finished in $(( $(date +%s) - START )) seconds: https://$domain"
