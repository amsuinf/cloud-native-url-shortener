terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state with locking. Create the bucket + DynamoDB table once
  # (see terraform/README.md), then `terraform init`. Commented so the repo
  # can be `terraform validate`-d without a real backend.
  #
  # backend "s3" {
  #   bucket         = "your-tfstate-bucket"
  #   key            = "url-shortener/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "url-shortener"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
