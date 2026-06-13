data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  # Use the first 3 AZs for multi-AZ resilience.
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
}

# Standard 3-AZ VPC: public subnets for the load balancers/NAT, private
# subnets for the worker nodes. Single NAT gateway keeps cost down for a
# portfolio; flip to one-per-AZ for true prod HA.
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.cluster_name}-vpc"
  cidr = var.vpc_cidr
  azs  = local.azs

  private_subnets = [for i in range(3) : cidrsubnet(var.vpc_cidr, 4, i)]
  public_subnets  = [for i in range(3) : cidrsubnet(var.vpc_cidr, 4, i + 8)]

  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true

  # Tags required by the AWS Load Balancer Controller / EKS subnet discovery.
  public_subnet_tags = {
    "kubernetes.io/role/elb"                    = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"           = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }
}
