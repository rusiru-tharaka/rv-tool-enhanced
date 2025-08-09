#!/bin/bash

# Complete Application Deployment using AWS CLI
# Deploys all components in the correct order using smartslot profile

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
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${PURPLE}================================================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}================================================================${NC}"
}

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

print_step() {
    echo -e "${CYAN}🔧 $1${NC}"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_header "RVTool Enhanced UX - Complete Application Deployment"

# Check prerequisites
print_step "Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed"
    exit 1
fi

# Check AWS profile
if ! aws configure list-profiles | grep -q "$AWS_PROFILE"; then
    print_error "AWS profile '$AWS_PROFILE' not found"
    exit 1
fi

# Test AWS credentials
print_info "Testing AWS credentials..."
aws sts get-caller-identity --profile "$AWS_PROFILE" --region "$AWS_REGION" > /dev/null
if [ $? -ne 0 ]; then
    print_error "AWS credentials test failed"
    exit 1
fi

print_status "Prerequisites check completed"

# Check current infrastructure status
print_step "Checking current infrastructure status..."

# Check storage stack
STORAGE_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$PROJECT_NAME-$ENVIRONMENT-storage" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null || echo "NOT_FOUND")

# Check database stack
DATABASE_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$PROJECT_NAME-$ENVIRONMENT-database-simple" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null || echo "NOT_FOUND")

# Check frontend stack
FRONTEND_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$PROJECT_NAME-$ENVIRONMENT-frontend" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null || echo "NOT_FOUND")

print_info "Infrastructure Status:"
print_info "  • Storage Stack: $STORAGE_STATUS"
print_info "  • Database Stack: $DATABASE_STATUS"
print_info "  • Frontend Stack: $FRONTEND_STATUS"

if [ "$STORAGE_STATUS" != "CREATE_COMPLETE" ] || [ "$DATABASE_STATUS" != "CREATE_COMPLETE" ] || [ "$FRONTEND_STATUS" != "CREATE_COMPLETE" ]; then
    print_error "Required infrastructure stacks are not deployed. Please deploy them first."
    exit 1
fi

print_status "Infrastructure is ready for application deployment"

# Step 1: Build and Push Backend Docker Image
print_header "Step 1: Building and Pushing Backend Docker Image"
if [ -f "$SCRIPT_DIR/build-and-push-backend.sh" ]; then
    chmod +x "$SCRIPT_DIR/build-and-push-backend.sh"
    "$SCRIPT_DIR/build-and-push-backend.sh"
else
    print_error "Backend build script not found"
    exit 1
fi

# Step 2: Update ECS Service
print_header "Step 2: Updating ECS Service"
if [ -f "$SCRIPT_DIR/update-ecs-service.sh" ]; then
    chmod +x "$SCRIPT_DIR/update-ecs-service.sh"
    "$SCRIPT_DIR/update-ecs-service.sh"
else
    print_error "ECS update script not found"
    exit 1
fi

# Step 3: Deploy Frontend Assets
print_header "Step 3: Deploying Frontend Assets"
if [ -f "$SCRIPT_DIR/deploy-frontend-assets.sh" ]; then
    chmod +x "$SCRIPT_DIR/deploy-frontend-assets.sh"
    "$SCRIPT_DIR/deploy-frontend-assets.sh"
else
    print_error "Frontend deployment script not found"
    exit 1
fi

# Step 4: Get Application URLs
print_header "Step 4: Application Deployment Summary"

# Get ALB DNS (if available)
ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name "$PROJECT_NAME-$ENVIRONMENT-compute" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApplicationLoadBalancerDNS`].OutputValue' \
    --output text 2>/dev/null || echo "Not available")

# Get CloudFront URL
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
    --stack-name "$PROJECT_NAME-$ENVIRONMENT-frontend" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionURL`].OutputValue' \
    --output text 2>/dev/null || echo "Not available")

# Get ECR Repository URI
ECR_URI=$(aws cloudformation describe-stacks \
    --stack-name "$PROJECT_NAME-$ENVIRONMENT-storage" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`BackendECRRepositoryURI`].OutputValue' \
    --output text 2>/dev/null || echo "Not available")

# Get Database endpoint
DB_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "$PROJECT_NAME-$ENVIRONMENT-database-simple" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' \
    --output text 2>/dev/null || echo "Not available")

print_status "🎉 Application deployment completed successfully!"

echo ""
print_info "📋 Deployment Summary:"
echo "  • Project: $PROJECT_NAME"
echo "  • Environment: $ENVIRONMENT"
echo "  • Region: $AWS_REGION"
echo "  • AWS Profile: $AWS_PROFILE"
echo ""
print_info "🌐 Access Points:"
echo "  • Frontend Application: $CLOUDFRONT_URL"
echo "  • Backend API (ALB): http://$ALB_DNS"
echo ""
print_info "🔧 Infrastructure Details:"
echo "  • ECR Repository: $ECR_URI"
echo "  • Database Endpoint: $DB_ENDPOINT"
echo ""
print_info "📊 Monitoring:"
echo "  • CloudWatch Console: https://$AWS_REGION.console.aws.amazon.com/cloudwatch/"
echo "  • ECS Console: https://$AWS_REGION.console.aws.amazon.com/ecs/"
echo "  • S3 Console: https://$AWS_REGION.console.aws.amazon.com/s3/"
echo ""
print_warning "⚠️  Next Steps:"
echo "  1. Test the frontend application at: $CLOUDFRONT_URL"
echo "  2. Verify backend API health checks"
echo "  3. Test file upload and processing functionality"
echo "  4. Monitor application logs in CloudWatch"
echo "  5. Set up database schema and initial data if needed"

print_status "Complete application deployment finished!"
