terraform {
  required_version = ">= 1.8"
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "PassIt"
      Environment = "staging"
      ManagedBy   = "Terraform"
      Course      = "CS5224"
    }
  }
}

# P1 adds reviewed module calls here after the shared AWS account,
# remote state and budget guardrails have been agreed by the team.
