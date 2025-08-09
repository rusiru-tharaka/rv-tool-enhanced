#!/bin/bash

# Simple Backend Deployment Script - No JQ Issues
# Deploys the enhanced FastAPI backend to AWS ECS
# Version: 1.2 - Simple and Reliable

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
AWS_PROFILE="smartslot"
AWS_REGION="us-east-1"
ECR_REPOSITORY="rvtool-api"
ECS_CLUSTER="rvtool-cluster-dev"
ECS_SERVICE="rvtool-api-dev"
TASK_DEFINITION="rvtool-api-dev"

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

echo -e "${BLUE}🚀 Simple Backend Deployment${NC}"
echo "ECR URI: $ECR_URI"

# Build and push image
cd backend
IMAGE_TAG="enhanced-$(date +%Y%m%d-%H%M%S)"
echo -e "${BLUE}Building image: $IMAGE_TAG${NC}"

# ECR login
aws ecr get-login-password --region $AWS_REGION --profile $AWS_PROFILE | \
    sudo docker login --username AWS --password-stdin $ECR_URI

# Build and push
sudo docker build -t $ECR_REPOSITORY:$IMAGE_TAG .
sudo docker tag $ECR_REPOSITORY:$IMAGE_TAG $ECR_URI:$IMAGE_TAG
sudo docker tag $ECR_REPOSITORY:$IMAGE_TAG $ECR_URI:latest
sudo docker push $ECR_URI:$IMAGE_TAG
sudo docker push $ECR_URI:latest

echo -e "${GREEN}✅ Image pushed: $ECR_URI:$IMAGE_TAG${NC}"

# Create new task definition JSON
LATEST_IMAGE_URI="$ECR_URI:$IMAGE_TAG"
cat > new-task-def.json << EOF
{
  "family": "$TASK_DEFINITION",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "rvtool-api",
      "image": "$LATEST_IMAGE_URI",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/rvtool-api-dev",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "AWS_DEFAULT_REGION", "value": "$AWS_REGION"},
        {"name": "LOG_LEVEL", "value": "info"},
        {"name": "WORKERS", "value": "2"}
      ],
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

echo -e "${BLUE}Registering new task definition...${NC}"
NEW_REVISION=$(aws ecs register-task-definition \
    --cli-input-json file://new-task-def.json \
    --profile $AWS_PROFILE \
    --region $AWS_REGION \
    --query 'taskDefinition.revision' \
    --output text)

echo -e "${GREEN}✅ New task definition: $TASK_DEFINITION:$NEW_REVISION${NC}"

# Update ECS service
echo -e "${BLUE}Updating ECS service...${NC}"
aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $ECS_SERVICE \
    --task-definition "$TASK_DEFINITION:$NEW_REVISION" \
    --profile $AWS_PROFILE \
    --region $AWS_REGION

echo -e "${BLUE}Waiting for deployment to complete...${NC}"
aws ecs wait services-stable \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE \
    --profile $AWS_PROFILE \
    --region $AWS_REGION

# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --names rvtool-alb-dev \
    --profile $AWS_PROFILE \
    --region $AWS_REGION \
    --query 'LoadBalancers[0].DNSName' \
    --output text)

echo -e "${GREEN}✅ Backend deployment completed!${NC}"
echo -e "${BLUE}ALB Endpoint: http://$ALB_DNS${NC}"
echo -e "${BLUE}Health Check: http://$ALB_DNS/health${NC}"
echo -e "${BLUE}API Docs: http://$ALB_DNS/docs${NC}"

# Test health endpoint
echo -e "${BLUE}Testing health endpoint...${NC}"
sleep 30
for i in {1..5}; do
    if curl -s -f "http://$ALB_DNS/health" > /dev/null; then
        echo -e "${GREEN}✅ Health check passed${NC}"
        break
    fi
    if [ $i -eq 5 ]; then
        echo -e "${YELLOW}⚠️  Health check failed after 5 attempts${NC}"
    else
        echo "Attempt $i/5 - waiting 30 seconds..."
        sleep 30
    fi
done

# Cleanup
rm -f new-task-def.json

cd ..
echo $LATEST_IMAGE_URI > latest_image_uri.txt
echo -e "${GREEN}🎉 Backend deployment completed successfully!${NC}"
