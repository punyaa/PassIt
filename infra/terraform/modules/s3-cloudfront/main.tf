# Private media bucket plus one CloudFront distribution that fronts the whole site:
#   /v1/*, /health, /docs, /openapi.json -> ALB (API, never cached)
#   /media/*, /thumbs/*                   -> S3 through origin access control
#   everything else                       -> ALB (Next.js web app)
# Uploads bypass CloudFront: the browser PUTs to S3 with a presigned URL.

data "aws_caller_identity" "current" {}

locals {
  bucket_name = "passit-${var.environment}-media-${data.aws_caller_identity.current.account_id}"
  alb_origin  = "alb"
  s3_origin   = "media"

  # AWS managed policies, referenced by ID so no extra resources are needed.
  caching_disabled        = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
  caching_optimized       = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  all_viewer_origin_reqs  = "216adef6-5c7f-47e4-b989-5492eafa07d3"
  cors_s3_origin_requests = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf"
}

# ---------------------------------------------------------------------------
# Bucket
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "media" {
  bucket = local.bucket_name

  # Condition photos are dispute evidence. Terraform must never delete them.
  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id

  versioning_configuration {
    status = "Enabled"
  }
}

# No lifecycle expiration rule on purpose.

# Separate resources so the bucket does not depend on the distribution that depends on it.
resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  cors_rule {
    allowed_methods = ["PUT", "GET", "HEAD"]
    allowed_origins = concat(
      ["https://${aws_cloudfront_distribution.site.domain_name}"],
      var.extra_cors_origins,
    )
    allowed_headers = ["Content-Type", "Content-MD5", "x-amz-*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

data "aws_iam_policy_document" "media_read_from_cloudfront" {
  statement {
    sid       = "AllowCloudFrontRead"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.media.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.site.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "media" {
  bucket = aws_s3_bucket.media.id
  policy = data.aws_iam_policy_document.media_read_from_cloudfront.json

  depends_on = [aws_s3_bucket_public_access_block.media]
}

# ---------------------------------------------------------------------------
# CloudFront
# ---------------------------------------------------------------------------

resource "aws_cloudfront_origin_access_control" "media" {
  name                              = "passit-${var.environment}-media"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "site" {
  enabled         = true
  comment         = "PassIt ${var.environment}"
  price_class     = "PriceClass_200"
  http_version    = "http2and3"
  is_ipv6_enabled = true

  origin {
    origin_id   = local.alb_origin
    domain_name = var.alb_dns_name

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "http-only"
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = 60
      origin_keepalive_timeout = 30
    }
  }

  origin {
    origin_id                = local.s3_origin
    domain_name              = aws_s3_bucket.media.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.media.id
  }

  # Next.js web app (and its static assets).
  default_cache_behavior {
    target_origin_id         = local.alb_origin
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = local.caching_disabled
    origin_request_policy_id = local.all_viewer_origin_reqs
    compress                 = true
  }

  dynamic "ordered_cache_behavior" {
    for_each = ["/v1/*", "/health", "/docs", "/openapi.json"]

    content {
      path_pattern             = ordered_cache_behavior.value
      target_origin_id         = local.alb_origin
      viewer_protocol_policy   = "redirect-to-https"
      allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods           = ["GET", "HEAD"]
      cache_policy_id          = local.caching_disabled
      origin_request_policy_id = local.all_viewer_origin_reqs
    }
  }

  # Photos and their thumbnails (written by the thumbnailer Lambda) live in the same bucket.
  dynamic "ordered_cache_behavior" {
    for_each = ["/media/*", "/thumbs/*"]

    content {
      path_pattern             = ordered_cache_behavior.value
      target_origin_id         = local.s3_origin
      viewer_protocol_policy   = "redirect-to-https"
      allowed_methods          = ["GET", "HEAD", "OPTIONS"]
      cached_methods           = ["GET", "HEAD"]
      cache_policy_id          = local.caching_optimized
      origin_request_policy_id = local.cors_s3_origin_requests
      compress                 = true
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
