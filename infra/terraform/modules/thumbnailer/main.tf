# Makes a small JPEG thumbnail for every listing photo as soon as it is uploaded.
#
#   browser PUT -> S3 media/listing/... -> S3 event -> this Lambda -> thumbs/listing/...
#
# The Lambda is a container image (Pillow has native code), so like the fee-release Lambda it
# needs the image pushed before the function exists. With image_tag null this module creates
# only the registry, role and log group; set image_tag once an image has been pushed. After
# that CI ships every new image and Terraform leaves the function's image alone.

data "aws_caller_identity" "current" {}

locals {
  name = "passit-${var.environment}"
}

resource "aws_ecr_repository" "thumbnailer" {
  name                 = "${local.name}-thumbnailer"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "keep_recent" {
  repository = aws_ecr_repository.thumbnailer.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the 20 most recent images so rollbacks stay possible"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 20 }
      action       = { type = "expire" }
    }]
  })
}

resource "aws_cloudwatch_log_group" "thumbnailer" {
  name              = "/aws/lambda/${local.name}-thumbnailer"
  retention_in_days = 7
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "thumbnailer" {
  name               = "${local.name}-thumbnailer"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.thumbnailer.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Read listing photos, write thumbnails, nothing else. Handover and return photos (damage
# evidence) are outside the read permission.
resource "aws_iam_role_policy" "bucket" {
  name = "thumbnails"
  role = aws_iam_role.thumbnailer.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadListingPhotos"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${var.bucket_arn}/${var.media_prefix}listing/*"
      },
      {
        Sid      = "WriteThumbnails"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${var.bucket_arn}/${var.thumbnail_prefix}*"
      },
    ]
  })
}

resource "aws_lambda_function" "thumbnailer" {
  count = var.image_tag == null ? 0 : 1

  function_name = "${local.name}-thumbnailer"
  role          = aws_iam_role.thumbnailer.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.thumbnailer.repository_url}:${var.image_tag}"
  architectures = ["arm64"]
  timeout       = 60
  memory_size   = 1024

  environment {
    variables = {
      MEDIA_PREFIX     = var.media_prefix
      THUMBNAIL_PREFIX = var.thumbnail_prefix
    }
  }

  depends_on = [aws_cloudwatch_log_group.thumbnailer, aws_iam_role_policy_attachment.logs]

  # CI ships a new image on every deploy, so Terraform only sets the first one.
  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_permission" "from_s3" {
  count = var.image_tag == null ? 0 : 1

  statement_id   = "AllowS3Invoke"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.thumbnailer[0].function_name
  principal      = "s3.amazonaws.com"
  source_arn     = var.bucket_arn
  source_account = data.aws_caller_identity.current.account_id
}

# A bucket has one notification configuration, and this module owns it. Only new listing
# photos trigger the function; the thumbnails it writes are under another prefix, so it can
# never trigger itself.
resource "aws_s3_bucket_notification" "photos" {
  count = var.image_tag == null ? 0 : 1

  bucket = var.bucket_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.thumbnailer[0].arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "${var.media_prefix}listing/"
  }

  depends_on = [aws_lambda_permission.from_s3]
}
