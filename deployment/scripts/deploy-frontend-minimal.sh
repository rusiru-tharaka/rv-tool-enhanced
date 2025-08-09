#!/bin/bash

# Deploy Minimal Frontend Stack
# Creates CloudFront distribution for React application

set -e

# Configuration
AWS_PROFILE="smartslot"
AWS_REGION="us-east-1"
PROJECT_NAME="rvtool-enhanced"
ENVIRONMENT="prod"
STACK_NAME="$PROJECT_NAME-$ENVIRONMENT-frontend"

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

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLOUDFORMATION_DIR="$SCRIPT_DIR/../aws/cloudformation"
TEMPLATE_FILE="$CLOUDFORMATION_DIR/05-frontend-minimal.yaml"

print_info "Deploying minimal frontend stack..."

# Check if stack exists and delete if it does
STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null || echo "DOES_NOT_EXIST")

if [ "$STACK_STATUS" != "DOES_NOT_EXIST" ]; then
    print_info "Deleting existing stack..."
    aws cloudformation delete-stack \
        --stack-name "$STACK_NAME" \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION"
    
    print_info "Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete \
        --stack-name "$STACK_NAME" \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION"
    
    print_status "Stack deleted successfully"
fi

# Validate template first
print_info "Validating CloudFormation template..."
aws cloudformation validate-template \
    --template-body "file://$TEMPLATE_FILE" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" > /dev/null

if [ $? -eq 0 ]; then
    print_status "Template validation successful"
else
    print_error "Template validation failed"
    exit 1
fi

# Deploy the frontend stack
print_info "Creating frontend stack..."
aws cloudformation create-stack \
    --stack-name "$STACK_NAME" \
    --template-body "file://$TEMPLATE_FILE" \
    --parameters "ParameterKey=Environment,ParameterValue=$ENVIRONMENT" \
                 "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME" \
                 "ParameterKey=PriceClass,ParameterValue=PriceClass_100" \
    --capabilities CAPABILITY_IAM \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --tags Key=Project,Value="$PROJECT_NAME" Key=Environment,Value="$ENVIRONMENT"

print_info "Waiting for stack creation to complete (this may take 10-15 minutes)..."
aws cloudformation wait stack-create-complete \
    --stack-name "$STACK_NAME" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION"

if [ $? -eq 0 ]; then
    print_status "Frontend stack deployed successfully!"
    
    # Get outputs
    print_info "Stack outputs:"
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
        
    # Get CloudFront URL for easy access
    CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionURL`].OutputValue' \
        --output text)
    
    print_info "🌐 Frontend Application URL: $CLOUDFRONT_URL"
    print_info "📝 Note: It may take a few minutes for the CloudFront distribution to be fully deployed"
    
else
    print_error "Frontend stack deployment failed!"
    
    # Show the failure events
    print_info "Failure events:"
    aws cloudformation describe-stack-events \
        --stack-name "$STACK_NAME" \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION" \
        --query 'StackEvents[?contains(ResourceStatus, `FAILED`)].[LogicalResourceId,ResourceStatusReason]' \
        --output table
    
    exit 1
fi
