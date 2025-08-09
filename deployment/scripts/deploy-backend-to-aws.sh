#!/bin/bash

# RVTool Enhanced Backend Deployment Script
# Deploys the enhanced FastAPI backend to AWS ECS
# Version: 1.0 - Production Deployment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
AWS_PROFILE="smartslot"
AWS_REGION="us-east-1"
ECR_REPOSITORY="rvtool-api"
ECS_CLUSTER="rvtool-cluster-dev"
ECS_SERVICE="rvtool-api-dev"
TASK_DEFINITION="rvtool-api-dev"
BACKEND_DIR="./backend"

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

# Function to print colored output
print_header() {
    echo -e "${PURPLE}================================================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}================================================================${NC}"
}

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_step() {
    echo -e "${CYAN}🔧 $1${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    print_header "🔍 Checking Prerequisites"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install AWS CLI."
        exit 1
    fi
    print_status "AWS CLI available"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install Docker."
        exit 1
    fi
    print_status "Docker available"
    
    # Check AWS credentials
    if ! aws sts get-caller-identity --profile $AWS_PROFILE &> /dev/null; then
        print_error "AWS credentials not configured for profile: $AWS_PROFILE"
        exit 1
    fi
    print_status "AWS credentials configured"
    
    # Check backend directory
    if [ ! -d "$BACKEND_DIR" ]; then
        print_error "Backend directory not found: $BACKEND_DIR"
        exit 1
    fi
    print_status "Backend directory found"
    
    # Check main application file
    if [ ! -f "$BACKEND_DIR/app_enhanced.py" ]; then
        print_error "Main application file not found: $BACKEND_DIR/app_enhanced.py"
        exit 1
    fi
    print_status "Main application file found"
    
    print_info "Account ID: $AWS_ACCOUNT_ID"
    print_info "ECR URI: $ECR_URI"
}

# Function to create Dockerfile if it doesn't exist
create_dockerfile() {
    print_header "📦 Preparing Docker Configuration"
    
    if [ ! -f "$BACKEND_DIR/Dockerfile" ]; then
        print_step "Creating production Dockerfile..."
        cat > "$BACKEND_DIR/Dockerfile" << 'EOF'
# RVTool Enhanced Backend - Production Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app_enhanced:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
EOF
        print_status "Dockerfile created"
    else
        print_status "Dockerfile already exists"
    fi
    
    # Ensure requirements.txt exists
    if [ ! -f "$BACKEND_DIR/requirements.txt" ]; then
        print_step "Creating requirements.txt..."
        cat > "$BACKEND_DIR/requirements.txt" << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
boto3==1.34.0
psycopg2-binary==2.9.9
pandas==2.1.4
openpyxl==3.1.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
requests==2.31.0
sqlalchemy==2.0.23
alembic==1.13.1
redis==5.0.1
celery==5.3.4
aiofiles==23.2.1
jinja2==3.1.2
EOF
        print_status "Requirements.txt created"
    else
        print_status "Requirements.txt already exists"
    fi
}

# Function to build and push Docker image
build_and_push_image() {
    print_header "🏗️  Building and Pushing Docker Image"
    
    cd "$BACKEND_DIR"
    
    # Get ECR login token
    print_step "Logging into ECR..."
    aws ecr get-login-password --region $AWS_REGION --profile $AWS_PROFILE | \
        docker login --username AWS --password-stdin $ECR_URI
    print_status "ECR login successful"
    
    # Build image
    IMAGE_TAG="enhanced-$(date +%Y%m%d-%H%M%S)"
    print_step "Building Docker image: $IMAGE_TAG"
    docker build -t $ECR_REPOSITORY:$IMAGE_TAG .
    docker tag $ECR_REPOSITORY:$IMAGE_TAG $ECR_URI:$IMAGE_TAG
    docker tag $ECR_REPOSITORY:$IMAGE_TAG $ECR_URI:latest
    print_status "Docker image built successfully"
    
    # Push image
    print_step "Pushing image to ECR..."
    docker push $ECR_URI:$IMAGE_TAG
    docker push $ECR_URI:latest
    print_status "Image pushed to ECR"
    
    # Store image URI for later use
    export LATEST_IMAGE_URI="$ECR_URI:$IMAGE_TAG"
    echo $LATEST_IMAGE_URI > ../latest_image_uri.txt
    
    cd ..
}

# Function to update ECS task definition
update_task_definition() {
    print_header "📋 Updating ECS Task Definition"
    
    # Get current task definition
    print_step "Retrieving current task definition..."
    CURRENT_TASK_DEF=$(aws ecs describe-task-definition \
        --task-definition $TASK_DEFINITION \
        --profile $AWS_PROFILE \
        --region $AWS_REGION)
    
    # Extract the task definition (without revision-specific fields)
    NEW_TASK_DEF=$(echo $CURRENT_TASK_DEF | jq '.taskDefinition | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)')
    
    # Update the image URI
    UPDATED_TASK_DEF=$(echo $NEW_TASK_DEF | jq --arg IMAGE_URI "$LATEST_IMAGE_URI" '.containerDefinitions[0].image = $IMAGE_URI')
    
    # Add enhanced environment variables
    ENHANCED_ENV='[
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "AWS_DEFAULT_REGION", "value": "us-east-1"},
        {"name": "LOG_LEVEL", "value": "info"},
        {"name": "WORKERS", "value": "2"}
    ]'
    
    FINAL_TASK_DEF=$(echo $UPDATED_TASK_DEF | jq --argjson ENV "$ENHANCED_ENV" '.containerDefinitions[0].environment += $ENV')
    
    # Register new task definition
    print_step "Registering new task definition..."
    NEW_REVISION=$(aws ecs register-task-definition \
        --cli-input-json "$FINAL_TASK_DEF" \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --query 'taskDefinition.revision' \
        --output text)
    
    print_status "New task definition registered: $TASK_DEFINITION:$NEW_REVISION"
    export NEW_TASK_DEFINITION_ARN="$TASK_DEFINITION:$NEW_REVISION"
}

# Function to update ECS service
update_ecs_service() {
    print_header "🚀 Updating ECS Service"
    
    print_step "Updating ECS service with new task definition..."
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $ECS_SERVICE \
        --task-definition $NEW_TASK_DEFINITION_ARN \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --query 'service.serviceName' \
        --output text
    
    print_status "ECS service update initiated"
    
    # Wait for deployment to complete
    print_step "Waiting for deployment to complete..."
    aws ecs wait services-stable \
        --cluster $ECS_CLUSTER \
        --services $ECS_SERVICE \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    print_status "Deployment completed successfully"
}

# Function to verify deployment
verify_deployment() {
    print_header "✅ Verifying Deployment"
    
    # Get ALB DNS name
    ALB_DNS=$(aws elbv2 describe-load-balancers \
        --names rvtool-alb-dev \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --query 'LoadBalancers[0].DNSName' \
        --output text)
    
    print_info "ALB DNS: $ALB_DNS"
    
    # Test health endpoint
    print_step "Testing health endpoint..."
    sleep 30  # Wait for service to be ready
    
    for i in {1..10}; do
        if curl -s -f "http://$ALB_DNS/health" > /dev/null; then
            print_status "Health check passed"
            break
        fi
        if [ $i -eq 10 ]; then
            print_warning "Health check failed after 10 attempts"
        else
            print_info "Attempt $i/10 - waiting 30 seconds..."
            sleep 30
        fi
    done
    
    # Get service status
    SERVICE_STATUS=$(aws ecs describe-services \
        --cluster $ECS_CLUSTER \
        --services $ECS_SERVICE \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --query 'services[0].status' \
        --output text)
    
    print_info "Service Status: $SERVICE_STATUS"
    
    # Get running tasks count
    RUNNING_TASKS=$(aws ecs describe-services \
        --cluster $ECS_CLUSTER \
        --services $ECS_SERVICE \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --query 'services[0].runningCount' \
        --output text)
    
    print_info "Running Tasks: $RUNNING_TASKS"
}

# Function to display deployment summary
display_summary() {
    print_header "🎉 Deployment Summary"
    
    echo ""
    print_status "✅ Backend deployment completed successfully!"
    echo ""
    print_info "📊 Deployment Details:"
    echo "  • Image: $LATEST_IMAGE_URI"
    echo "  • Task Definition: $NEW_TASK_DEFINITION_ARN"
    echo "  • ECS Cluster: $ECS_CLUSTER"
    echo "  • ECS Service: $ECS_SERVICE"
    echo ""
    print_info "🌐 Access Points:"
    echo "  • ALB Endpoint: http://$ALB_DNS"
    echo "  • Health Check: http://$ALB_DNS/health"
    echo "  • API Docs: http://$ALB_DNS/docs"
    echo ""
    print_info "📋 Next Steps:"
    echo "  1. Deploy frontend to complete the full application"
    echo "  2. Run end-to-end tests"
    echo "  3. Monitor application performance"
    echo ""
}

# Function to rollback on failure
rollback_deployment() {
    print_error "Deployment failed. Initiating rollback..."
    
    # Get previous task definition
    PREVIOUS_REVISION=$((NEW_REVISION - 1))
    if [ $PREVIOUS_REVISION -gt 0 ]; then
        print_step "Rolling back to revision $PREVIOUS_REVISION..."
        aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service $ECS_SERVICE \
            --task-definition "$TASK_DEFINITION:$PREVIOUS_REVISION" \
            --profile $AWS_PROFILE \
            --region $AWS_REGION \
            --query 'service.serviceName' \
            --output text
        
        print_status "Rollback initiated"
    else
        print_warning "No previous revision available for rollback"
    fi
}

# Main execution function
main() {
    print_header "🚀 RVTool Enhanced Backend Deployment"
    echo ""
    print_info "Starting deployment process..."
    echo ""
    
    # Set trap for error handling
    trap rollback_deployment ERR
    
    # Execute deployment steps
    check_prerequisites
    create_dockerfile
    build_and_push_image
    update_task_definition
    update_ecs_service
    verify_deployment
    display_summary
    
    print_status "🎉 Deployment completed successfully!"
}

# Execute main function
main "$@"
