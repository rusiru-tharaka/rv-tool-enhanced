#!/bin/bash

# RVTool Enhanced UX - Infrastructure Deployment Script
# Deploys all CloudFormation stacks in the correct order
# Version: 1.0 - Production Grade Infrastructure

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
PROJECT_NAME="rvtool-enhanced"
ENVIRONMENT="prod"
DEPLOYMENT_LOG="infrastructure_deployment_$(date +%Y%m%d_%H%M%S).log"

# Email for alerts (update this)
ALERT_EMAIL="admin@example.com"

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

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$DEPLOYMENT_LOG"
    echo "$1"
}

# Function to check if stack exists
stack_exists() {
    local stack_name=$1
    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION" \
        --output text \
        --query 'Stacks[0].StackStatus' 2>/dev/null || echo "DOES_NOT_EXIST"
}

# Function to wait for stack operation to complete
wait_for_stack() {
    local stack_name=$1
    local operation=$2
    
    print_info "Waiting for stack $stack_name to complete $operation..."
    
    aws cloudformation wait "stack-${operation}-complete" \
        --stack-name "$stack_name" \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION"
    
    if [ $? -eq 0 ]; then
        print_status "Stack $stack_name $operation completed successfully"
        return 0
    else
        print_error "Stack $stack_name $operation failed"
        return 1
    fi
}

# Function to deploy or update stack
deploy_stack() {
    local stack_name=$1
    local template_file=$2
    shift 2
    local parameters=("$@")
    
    print_step "Deploying stack: $stack_name"
    log_message "Starting deployment of stack: $stack_name"
    
    local stack_status=$(stack_exists "$stack_name")
    
    if [ "$stack_status" = "DOES_NOT_EXIST" ]; then
        print_info "Creating new stack: $stack_name"
        aws cloudformation create-stack \
            --stack-name "$stack_name" \
            --template-body "file://$template_file" \
            --parameters "${parameters[@]}" \
            --capabilities CAPABILITY_NAMED_IAM \
            --profile "$AWS_PROFILE" \
            --region "$AWS_REGION" \
            --tags Key=Project,Value="$PROJECT_NAME" Key=Environment,Value="$ENVIRONMENT" Key=ManagedBy,Value=CloudFormation
        
        wait_for_stack "$stack_name" "create"
    else
        print_info "Updating existing stack: $stack_name"
        aws cloudformation update-stack \
            --stack-name "$stack_name" \
            --template-body "file://$template_file" \
            --parameters "${parameters[@]}" \
            --capabilities CAPABILITY_NAMED_IAM \
            --profile "$AWS_PROFILE" \
            --region "$AWS_REGION" \
            --tags Key=Project,Value="$PROJECT_NAME" Key=Environment,Value="$ENVIRONMENT" Key=ManagedBy,Value=CloudFormation 2>/dev/null
        
        if [ $? -eq 0 ]; then
            wait_for_stack "$stack_name" "update"
        else
            print_warning "No updates to perform for stack: $stack_name"
        fi
    fi
    
    log_message "Completed deployment of stack: $stack_name"
}

# Function to validate template
validate_template() {
    local template_file=$1
    print_info "Validating template: $template_file"
    
    aws cloudformation validate-template \
        --template-body "file://$template_file" \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION" > /dev/null
    
    if [ $? -eq 0 ]; then
        print_status "Template validation successful: $template_file"
    else
        print_error "Template validation failed: $template_file"
        exit 1
    fi
}

# Main deployment function
main() {
    print_header "RVTool Enhanced UX - Infrastructure Deployment"
    
    # Check prerequisites
    print_step "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
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
    
    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    CLOUDFORMATION_DIR="$SCRIPT_DIR/../aws/cloudformation"
    
    # Validate all templates first
    print_step "Validating CloudFormation templates..."
    validate_template "$CLOUDFORMATION_DIR/01-vpc-networking.yaml"
    validate_template "$CLOUDFORMATION_DIR/02-database.yaml"
    validate_template "$CLOUDFORMATION_DIR/03-storage.yaml"
    validate_template "$CLOUDFORMATION_DIR/04-compute.yaml"
    validate_template "$CLOUDFORMATION_DIR/05-frontend.yaml"
    validate_template "$CLOUDFORMATION_DIR/06-monitoring.yaml"
    
    print_status "All templates validated successfully"
    
    # Deploy stacks in order
    print_header "Deploying Infrastructure Stacks"
    
    # Phase 1: VPC and Networking
    deploy_stack \
        "$PROJECT_NAME-$ENVIRONMENT-vpc" \
        "$CLOUDFORMATION_DIR/01-vpc-networking.yaml" \
        "ParameterKey=Environment,ParameterValue=$ENVIRONMENT" \
        "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME"
    
    # Phase 2: Database and Caching
    deploy_stack \
        "$PROJECT_NAME-$ENVIRONMENT-database" \
        "$CLOUDFORMATION_DIR/02-database.yaml" \
        "ParameterKey=Environment,ParameterValue=$ENVIRONMENT" \
        "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME"
    
    # Phase 3: Storage
    deploy_stack \
        "$PROJECT_NAME-$ENVIRONMENT-storage" \
        "$CLOUDFORMATION_DIR/03-storage.yaml" \
        "ParameterKey=Environment,ParameterValue=$ENVIRONMENT" \
        "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME"
    
    # Phase 4: Compute (ECS and ALB)
    deploy_stack \
        "$PROJECT_NAME-$ENVIRONMENT-compute" \
        "$CLOUDFORMATION_DIR/04-compute.yaml" \
        "ParameterKey=Environment,ParameterValue=$ENVIRONMENT" \
        "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME"
    
    # Phase 5: Frontend (CloudFront)
    deploy_stack \
        "$PROJECT_NAME-$ENVIRONMENT-frontend" \
        "$CLOUDFORMATION_DIR/05-frontend.yaml" \
        "ParameterKey=Environment,ParameterValue=$ENVIRONMENT" \
        "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME"
    
    # Phase 6: Monitoring
    deploy_stack \
        "$PROJECT_NAME-$ENVIRONMENT-monitoring" \
        "$CLOUDFORMATION_DIR/06-monitoring.yaml" \
        "ParameterKey=Environment,ParameterValue=$ENVIRONMENT" \
        "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME" \
        "ParameterKey=AlertEmail,ParameterValue=$ALERT_EMAIL"
    
    # Get deployment outputs
    print_header "Deployment Summary"
    
    print_info "Getting deployment outputs..."
    
    # Get ALB DNS name
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
        --stack-name "$PROJECT_NAME-$ENVIRONMENT-database" \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' \
        --output text 2>/dev/null || echo "Not available")
    
    print_status "Infrastructure deployment completed successfully!"
    
    echo ""
    print_info "📋 Deployment Summary:"
    echo "  • Project: $PROJECT_NAME"
    echo "  • Environment: $ENVIRONMENT"
    echo "  • Region: $AWS_REGION"
    echo "  • Deployment Log: $DEPLOYMENT_LOG"
    echo ""
    print_info "🌐 Access Points:"
    echo "  • Application Load Balancer: http://$ALB_DNS"
    echo "  • CloudFront Distribution: $CLOUDFRONT_URL"
    echo ""
    print_info "🔧 Infrastructure Details:"
    echo "  • ECR Repository: $ECR_URI"
    echo "  • Database Endpoint: $DB_ENDPOINT"
    echo ""
    print_info "📊 Monitoring:"
    echo "  • CloudWatch Console: https://$AWS_REGION.console.aws.amazon.com/cloudwatch/"
    echo "  • ECS Console: https://$AWS_REGION.console.aws.amazon.com/ecs/"
    echo ""
    print_warning "⚠️  Next Steps:"
    echo "  1. Build and push Docker images to ECR"
    echo "  2. Update ECS service with new task definition"
    echo "  3. Deploy frontend to S3 and invalidate CloudFront"
    echo "  4. Configure database schema and initial data"
    echo "  5. Test the complete application"
    
    log_message "Infrastructure deployment completed successfully"
}

# Run main function
main "$@"
