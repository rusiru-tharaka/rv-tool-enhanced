#!/bin/bash

# Update ECS Service with New Docker Image
# Uses AWS CLI with smartslot profile

set -e

# Configuration
AWS_PROFILE="smartslot"
AWS_REGION="us-east-1"
PROJECT_NAME="rvtool-enhanced"
ENVIRONMENT="prod"
CLUSTER_NAME="$PROJECT_NAME-$ENVIRONMENT-cluster"
SERVICE_NAME="$PROJECT_NAME-$ENVIRONMENT-backend-service"
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

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info "Updating ECS service with new Docker image..."

# Check if ECS cluster exists
print_info "Checking if ECS cluster exists..."
CLUSTER_STATUS=$(aws ecs describe-clusters \
    --clusters $CLUSTER_NAME \
    --profile $AWS_PROFILE \
    --region $AWS_REGION \
    --query 'clusters[0].status' \
    --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$CLUSTER_STATUS" != "ACTIVE" ]; then
    print_error "ECS cluster $CLUSTER_NAME not found or not active"
    print_info "Creating ECS cluster..."
    
    aws ecs create-cluster \
        --cluster-name $CLUSTER_NAME \
        --capacity-providers FARGATE FARGATE_SPOT \
        --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 capacityProvider=FARGATE_SPOT,weight=4 \
        --settings name=containerInsights,value=enabled \
        --tags key=Name,value=$CLUSTER_NAME key=Environment,value=$ENVIRONMENT key=Project,value=$PROJECT_NAME \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    print_status "ECS cluster created"
else
    print_status "ECS cluster is active"
fi

# Get current task definition
print_info "Getting current task definition..."
CURRENT_TASK_DEF=$(aws ecs describe-task-definition \
    --task-definition $TASK_FAMILY \
    --profile $AWS_PROFILE \
    --region $AWS_REGION \
    --query 'taskDefinition' 2>/dev/null || echo "null")

if [ "$CURRENT_TASK_DEF" = "null" ]; then
    print_warning "Task definition not found. Creating a new one..."
    
    # Create a basic task definition
    cat > /tmp/task-definition.json << EOF
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
                    "name": "DATABASE_URL",
                    "valueFrom": "arn:aws:secretsmanager:us-east-1:783764609930:secret:rvtool-enhanced-prod-db-credentials-simple-o2ceit"
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

    # Create CloudWatch log group
    aws logs create-log-group \
        --log-group-name "/ecs/$TASK_FAMILY" \
        --profile $AWS_PROFILE \
        --region $AWS_REGION 2>/dev/null || true

    # Register task definition
    aws ecs register-task-definition \
        --cli-input-json file:///tmp/task-definition.json \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    print_status "Task definition created"
else
    print_info "Updating existing task definition with new image..."
    
    # Get the current task definition and update the image
    aws ecs describe-task-definition \
        --task-definition $TASK_FAMILY \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --query 'taskDefinition' | \
    jq --arg image "$ECR_REPOSITORY:latest" '.containerDefinitions[0].image = $image | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' > /tmp/updated-task-definition.json
    
    # Register updated task definition
    aws ecs register-task-definition \
        --cli-input-json file:///tmp/updated-task-definition.json \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    print_status "Task definition updated"
fi

# Check if service exists
print_info "Checking if ECS service exists..."
SERVICE_STATUS=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --profile $AWS_PROFILE \
    --region $AWS_REGION \
    --query 'services[0].status' \
    --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$SERVICE_STATUS" = "NOT_FOUND" ] || [ "$SERVICE_STATUS" = "None" ]; then
    print_warning "ECS service not found. Creating new service..."
    
    # Create ECS service
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --task-definition $TASK_FAMILY \
        --desired-count 1 \
        --launch-type FARGATE \
        --platform-version LATEST \
        --network-configuration "awsvpcConfiguration={subnets=[subnet-09ec0d48a194d8ab5,subnet-06258a3e8e6dc7177],securityGroups=[sg-08214a4aca0dfe080],assignPublicIp=DISABLED}" \
        --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:783764609930:targetgroup/rvtool-enhanced-prod-backend-tg/12345,containerName=backend,containerPort=8000 \
        --health-check-grace-period-seconds 300 \
        --deployment-configuration "maximumPercent=200,minimumHealthyPercent=50,deploymentCircuitBreaker={enable=true,rollback=true}" \
        --tags key=Name,value=$SERVICE_NAME key=Environment,value=$ENVIRONMENT \
        --profile $AWS_PROFILE \
        --region $AWS_REGION 2>/dev/null || \
    
    # If load balancer fails, create without it
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --task-definition $TASK_FAMILY \
        --desired-count 1 \
        --launch-type FARGATE \
        --platform-version LATEST \
        --network-configuration "awsvpcConfiguration={subnets=[subnet-09ec0d48a194d8ab5,subnet-06258a3e8e6dc7177],securityGroups=[sg-08214a4aca0dfe080],assignPublicIp=DISABLED}" \
        --health-check-grace-period-seconds 300 \
        --deployment-configuration "maximumPercent=200,minimumHealthyPercent=50,deploymentCircuitBreaker={enable=true,rollback=true}" \
        --tags key=Name,value=$SERVICE_NAME key=Environment,value=$ENVIRONMENT \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    print_status "ECS service created"
else
    print_info "Updating existing ECS service..."
    
    # Update service with new task definition
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --task-definition $TASK_FAMILY \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    print_status "ECS service updated"
fi

# Wait for service to stabilize
print_info "Waiting for service to stabilize (this may take a few minutes)..."
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --profile $AWS_PROFILE \
    --region $AWS_REGION

print_status "ECS service deployment completed!"

# Get service status
print_info "Service status:"
aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --profile $AWS_PROFILE \
    --region $AWS_REGION \
    --query 'services[0].{ServiceName:serviceName,Status:status,RunningCount:runningCount,DesiredCount:desiredCount,TaskDefinition:taskDefinition}' \
    --output table

# Clean up temp files
rm -f /tmp/task-definition.json /tmp/updated-task-definition.json

print_status "ECS service update completed!"
