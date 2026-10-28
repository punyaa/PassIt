variable "environment" {
  type = string
}

variable "bucket_name" {
  description = "The media bucket."
  type        = string
}

variable "bucket_arn" {
  type = string
}

variable "media_prefix" {
  description = "Where uploads live. Must match PASSIT_S3_PREFIX."
  type        = string
  default     = "media/"
}

variable "thumbnail_prefix" {
  description = "Where thumbnails are written. Must match PASSIT_THUMBNAIL_PREFIX and the CloudFront route."
  type        = string
  default     = "thumbs/"
}

variable "image_tag" {
  description = "Thumbnailer image tag in ECR. Null creates only the registry, role and log group, so the first image can be pushed."
  type        = string
  default     = null
}
