#!/usr/bin/env bash
# Make thumbnails for listing photos that were uploaded before the thumbnailer existed.
#
#   AWS_PROFILE=nus-sso scripts/thumbnails/backfill.sh staging
#
# New uploads are thumbnailed automatically. This walks the existing listing photos and
# invokes the thumbnailer Lambda for each, with the same event S3 would have sent. Safe to
# repeat: a thumbnail is simply written again.
set -euo pipefail

ENV_NAME="${1:-}"
case "$ENV_NAME" in
  staging | demo) ;;
  *) echo "usage: $0 staging|demo" >&2; exit 2 ;;
esac

export AWS_REGION="${AWS_REGION:-ap-southeast-1}" AWS_PAGER=""
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
BUCKET="passit-$ENV_NAME-media-$ACCOUNT"
FUNCTION="passit-$ENV_NAME-thumbnailer"
PREFIX="${PASSIT_S3_PREFIX:-media/}listing/"

aws lambda get-function --function-name "$FUNCTION" >/dev/null 2>&1 ||
  { echo "No function $FUNCTION: give Terraform a thumbnailer_image_tag first." >&2; exit 1; }

count=0
while IFS=$'\t' read -r key size; do
  [ -n "$key" ] && [ "$key" != "None" ] || continue
  event=$(python3 -c 'import json,sys; print(json.dumps({"Records":[{"s3":{"bucket":{"name":sys.argv[1]},"object":{"key":sys.argv[2],"size":int(sys.argv[3])}}}]}))' "$BUCKET" "$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote_plus(sys.argv[1]))' "$key")" "$size")
  aws lambda invoke --function-name "$FUNCTION" --cli-binary-format raw-in-base64-out \
    --payload "$event" /dev/null >/dev/null
  count=$((count + 1))
done < <(aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "$PREFIX" \
  --query 'Contents[].[Key,Size]' --output text)

echo "Asked $FUNCTION to thumbnail $count photo(s) under s3://$BUCKET/$PREFIX"
