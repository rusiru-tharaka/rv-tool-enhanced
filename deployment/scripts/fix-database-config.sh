#!/bin/bash

# Fix Database Configuration in ECS Task Definition
# Updates task definition to use proper database environment variables

set -e

# Configuration
AWS_PROFILE="smartslot"
AWS_REGION="us-east-1"
PROJECT_NAME="rvtool-enhanced"
ENVIRONMENT="prod"
TASK_FAMILY="$PROJECT_NAME-$ENVIRONMENT-backend"
ECR_REPOSITORY="783764609930.dkr.ecr.us-east-1.amazonaws.com/rvtool-enhanced-prod-backend"

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

print_info "Updating task definition with proper database configuration..."

# Create updated task definition
cat > /tmp/updated-task-definition.json << EOF
{
    "family": "$TASK_FAMILY",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "512",
    "memory": "1024",
    "executionRoleArn": "arn:aws:iam::783764609930:role/rvtool-enhanced-prod-ecs-execution-role",
    "taskRoleArn": "arn:aws:iam::783764609930:role/rvtool-enhanced-prod-ecs-task-role",
    "containerDefinitions": [
        {
            "name": "backend",
            "image": "$ECR_REPOSITORY:latest",
            "essential": true,
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {"name": "ENVIRONMENT", "value": "$ENVIRONMENT"},
                {"name": "DATABASE_HOST", "value": "rvtool-enhanced-prod-database-simple.cnqaaqqw4215.us-east-1.rds.amazonaws.com"},
                {"name": "DATABASE_PORT", "value": "5432"},
                {"name": "DATABASE_NAME", "value": "rvtool_enhanced"},
                {"name": "REDIS_HOST", "value": "localhost"},
                {"name": "REDIS_PORT", "value": "6379"},
                {"name": "S3_BUCKET_NAME", "value": "rvtool-enhanced-prod-files-783764609930"},
                {"name": "AWS_DEFAULT_REGION", "value": "$AWS_REGION"}
            ],
            "secrets": [
                {
                    "name": "DATABASE_USERNAME",
                    "valueFrom": "arn:aws:secretsmanager:us-east-1:783764609930:secret:rvtool-enhanced-prod-db-credentials-simple-o2ceit:username::"
                },
                {
                    "name": "DATABASE_PASSWORD", 
                    "valueFrom": "arn:aws:secretsmanager:us-east-1:783764609930:secret:rvtool-enhanced-prod-db-credentials-simple-o2ceit:password::"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/$TASK_FAMILY",
                    "awslogs-region": "$AWS_REGION",
                    "awslogs-stream-prefix": "ecs"
                }
            },
            "healthCheck": {
                "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 60
            }
        }
    ]
}
EOF

# Register updated task definition
print_info "Registering updated task definition..."
aws ecs register-task-definition \
    --cli-input-json file:///tmp/updated-task-definition.json \
    --profile $AWS_PROFILE \
    --region $AWS_REGION

print_status "Task definition updated"

# Update service to use new task definition
print_info "Updating ECS service..."
aws ecs update-service \
    --cluster $PROJECT_NAME-$ENVIRONMENT-cluster \
    --service $PROJECT_NAME-$ENVIRONMENT-backend-service \
    --task-definition $TASK_FAMILY \
    --profile $AWS_PROFILE \
    --region $AWS_REGION

print_status "ECS service updated"

# Clean up temp files
rm -f /tmp/updated-task-definition.json

print_status "Database configuration fix completed!"
