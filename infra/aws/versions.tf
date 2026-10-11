terraform {
  required_version = ">= 1.5" # import blocks

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.68"
    }
  }

  # Local state for now. For shared use, move to an S3 backend with
  # use_lockfile = true (native S3 locking, no DynamoDB table needed).
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project    = "ai-assurance-pipeline"
      managed-by = "terraform"
      repo       = var.github_repository
    }
  }
}
