# Terraform — AWS EKS Infrastructure

Provisions everything the platform runs on:

- **VPC** across 3 AZs (public + private subnets, NAT gateway)
- **EKS** control plane (v1.31) with IRSA enabled
- **Managed node group** (autoscaling 2–6 × t3.medium)
- **Core add-ons**: CoreDNS, kube-proxy, VPC-CNI, EBS CSI driver

## Prerequisites

- Terraform >= 1.5, AWS CLI configured with credentials
- (Recommended) An S3 bucket + DynamoDB table for remote state

## One-time remote-state bootstrap

```bash
aws s3 mb s3://your-tfstate-bucket --region us-east-1
aws dynamodb create-table \
  --table-name terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST --region us-east-1
```

Then uncomment the `backend "s3"` block in `versions.tf`.

## Usage

```bash
terraform init
terraform plan  -out tfplan
terraform apply tfplan

# Wire up kubectl
$(terraform output -raw configure_kubectl)
kubectl get nodes
```

## Teardown

```bash
terraform destroy
```

> 💰 **Cost note:** EKS control plane (~$0.10/hr) + EC2 nodes + NAT gateway
> bill while running. Destroy when you're done demoing.
