#!/bin/bash

# Create ECS IAM Roles
# Creates the necessary IAM roles for ECS tasks

set -e

# Configuration
AWS_PROFILE="smartslot"
AWS_REGION="us-east-1"
PROJECT_NAME="rvtool-enhanced"
ENVIRONMENT="prod"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_info "Creating ECS IAM roles..."

# Create ECS Task Execution Role
print_info "Creating ECS Task Execution Role..."

# Trust policy for ECS tasks
cat > /tmp/ecs-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create ECS Task Execution Role
aws iam create-role \
    --role-name rvtool-enhanced-prod-ecs-execution-role \
    --assume-role-policy-document file:///tmp/ecs-trust-policy.json \
    --description "ECS Task Execution Role for RVTool Enhanced" \
    --profile $AWS_PROFILE \
    --region $AWS_REGION

# Attach managed policy for ECS task execution
aws iam attach-role-policy \
    --role-name rvtool-enhanced-prod-ecs-execution-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
    --profile $AWS_PROFILE \
    --region $AWS_REGION

# Create custom policy for Secrets Manager access
cat > /tmp/secrets-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:783764609930:secret:rvtool-enhanced-prod-db-credentials-simple-*"
      ]
    }
  ]
}
EOF

aws iam create-policy \
    --policy-name rvtool-enhanced-prod-secrets-access \
    --policy-document file:///tmp/secrets-policy.json \
    --description "Access to RVTool Enhanced secrets" \
    --profile $AWS_PROFILE \
    --region $AWS_REGION

aws iam attach-role-policy \
    --role-name rvtool-enhanced-prod-ecs-execution-role \
    --policy-arn arn:aws:iam::783764609930:policy/rvtool-enhanced-prod-secrets-access \
    --profile $AWS_PROFILE \
    --region $AWS_REGION

print_status "ECS Task Execution Role created"

# Create ECS Task Role
print_info "Creating ECS Task Role..."

aws iam create-role \
    --role-name rvtool-enhanced-prod-ecs-task-role \
    --assume-role-policy-document file:///tmp/ecs-trust-policy.json \
    --description "ECS Task Role for RVTool Enhanced" \
    --profile $AWS_PROFILE \
    --region $AWS_REGION

# Create custom policy for S3 and Bedrock access
cat > /tmp/task-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::rvtool-enhanced-prod-files-783764609930",
        "arn:aws:s3:::rvtool-enhanced-prod-files-783764609930/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-*",
        "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-*"
      ]
    }
  ]
}
EOF

aws iam create-policy \
    --policy-name rvtool-enhanced-prod-task-permissions \
    --policy-document file:///tmp/task-policy.json \
    --description "Task permissions for RVTool Enhanced" \
    --profile $AWS_PROFILE \
    --region $AWS_REGION

aws iam attach-role-policy \
    --role-name rvtool-enhanced-prod-ecs-task-role \
    --policy-arn arn:aws:iam::783764609930:policy/rvtool-enhanced-prod-task-permissions \
    --profile $AWS_PROFILE \
    --region $AWS_REGION

print_status "ECS Task Role created"

# Clean up temp files
rm -f /tmp/ecs-trust-policy.json /tmp/secrets-policy.json /tmp/task-policy.json

print_status "All ECS IAM roles created successfully!"

# Wait a moment for IAM consistency
print_info "Waiting for IAM consistency..."
sleep 10

print_status "ECS IAM roles setup completed!"
