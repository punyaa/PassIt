terraform {
  required_version = ">= 1.8"
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "PassIt"
      Environment = "demo"
      ManagedBy   = "Terraform"
      Course      = "CS5224"
    }
  }
}

# Demo module calls are promoted from staging after the weekly gate passes.
