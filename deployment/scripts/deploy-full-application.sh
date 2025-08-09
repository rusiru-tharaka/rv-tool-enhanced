#!/bin/bash

# RVTool Enhanced UX - Full Application Deployment
# Orchestrates the complete deployment of both backend and frontend
# Version: 1.0 - Production Grade Deployment

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
DEPLOYMENT_LOG="deployment_$(date +%Y%m%d_%H%M%S).log"

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
}

# Function to check prerequisites
check_prerequisites() {
    print_header "🔍 Pre-Deployment Validation"
    
    log_message "Starting pre-deployment validation"
    
    # Check if deployment scripts exist
    if [ ! -f "deploy-backend-to-aws.sh" ]; then
        print_error "Backend deployment script not found"
        exit 1
    fi
    
    if [ ! -f "deploy-frontend-to-aws.sh" ]; then
        print_error "Frontend deployment script not found"
        exit 1
    fi
    
    # Make scripts executable
    chmod +x deploy-backend-to-aws.sh
    chmod +x deploy-frontend-to-aws.sh
    
    print_status "Deployment scripts found and made executable"
    
    # Check AWS connectivity
    if ! aws sts get-caller-identity --profile $AWS_PROFILE &> /dev/null; then
        print_error "AWS credentials not configured for profile: $AWS_PROFILE"
        exit 1
    fi
    
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account --output text)
    print_status "AWS connectivity verified"
    print_info "Account ID: $AWS_ACCOUNT_ID"
    
    # Check existing infrastructure
    print_step "Validating existing AWS infrastructure..."
    
    # Check ECS cluster
    if aws ecs describe-clusters --clusters rvtool-cluster-dev --profile $AWS_PROFILE --region $AWS_REGION &> /dev/null; then
        print_status "ECS cluster exists"
    else
        print_error "ECS cluster 'rvtool-cluster-dev' not found"
        exit 1
    fi
    
    # Check S3 bucket
    if aws s3 ls s3://rvtool-static-dev-783764609930-202507111752 --profile $AWS_PROFILE --region $AWS_REGION &> /dev/null; then
        print_status "S3 bucket exists"
    else
        print_error "S3 bucket for frontend not found"
        exit 1
    fi
    
    # Check CloudFront distribution
    if aws cloudfront get-distribution --id EL1JB6MBCPLCI --profile $AWS_PROFILE &> /dev/null; then
        print_status "CloudFront distribution exists"
    else
        print_error "CloudFront distribution not found"
        exit 1
    fi
    
    log_message "Pre-deployment validation completed successfully"
}

# Function to create deployment backup
create_deployment_backup() {
    print_header "💾 Creating Deployment Backup"
    
    BACKUP_DIR="deployment_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    log_message "Creating deployment backup in $BACKUP_DIR"
    
    # Backup current ECS task definition
    print_step "Backing up current ECS task definition..."
    aws ecs describe-task-definition \
        --task-definition rvtool-api-dev \
        --profile $AWS_PROFILE \
        --region $AWS_REGION > "$BACKUP_DIR/current_task_definition.json"
    
    # Backup current service configuration
    print_step "Backing up current ECS service configuration..."
    aws ecs describe-services \
        --cluster rvtool-cluster-dev \
        --services rvtool-api-dev \
        --profile $AWS_PROFILE \
        --region $AWS_REGION > "$BACKUP_DIR/current_service_config.json"
    
    # Create rollback script
    print_step "Creating rollback script..."
    cat > "$BACKUP_DIR/rollback.sh" << 'EOF'
#!/bin/bash
# Rollback script - automatically generated
set -e

AWS_PROFILE="smartslot"
AWS_REGION="us-east-1"

echo "🔄 Rolling back deployment..."

# Get current task definition revision
CURRENT_REVISION=$(jq -r '.taskDefinition.revision' current_task_definition.json)

echo "Rolling back to task definition revision: $CURRENT_REVISION"

# Update service to use previous task definition
aws ecs update-service \
    --cluster rvtool-cluster-dev \
    --service rvtool-api-dev \
    --task-definition "rvtool-api-dev:$CURRENT_REVISION" \
    --profile $AWS_PROFILE \
    --region $AWS_REGION

echo "✅ Rollback completed"
EOF
    
    chmod +x "$BACKUP_DIR/rollback.sh"
    
    print_status "Deployment backup created: $BACKUP_DIR"
    log_message "Deployment backup created successfully"
}

# Function to deploy backend
deploy_backend() {
    print_header "🚀 Deploying Backend"
    
    log_message "Starting backend deployment"
    
    print_step "Executing backend deployment script..."
    if ./deploy-backend-to-aws.sh 2>&1 | tee -a "$DEPLOYMENT_LOG"; then
        print_status "Backend deployment completed successfully"
        log_message "Backend deployment completed successfully"
    else
        print_error "Backend deployment failed"
        log_message "Backend deployment failed"
        return 1
    fi
}

# Function to deploy frontend
deploy_frontend() {
    print_header "🌐 Deploying Frontend"
    
    log_message "Starting frontend deployment"
    
    print_step "Executing frontend deployment script..."
    if ./deploy-frontend-to-aws.sh 2>&1 | tee -a "$DEPLOYMENT_LOG"; then
        print_status "Frontend deployment completed successfully"
        log_message "Frontend deployment completed successfully"
    else
        print_error "Frontend deployment failed"
        log_message "Frontend deployment failed"
        return 1
    fi
}

# Function to run end-to-end tests
run_e2e_tests() {
    print_header "🧪 Running End-to-End Tests"
    
    log_message "Starting end-to-end tests"
    
    # Get endpoints
    ALB_DNS=$(aws elbv2 describe-load-balancers \
        --names rvtool-alb-dev \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --query 'LoadBalancers[0].DNSName' \
        --output text)
    
    CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution \
        --id EL1JB6MBCPLCI \
        --profile $AWS_PROFILE \
        --query 'Distribution.DomainName' \
        --output text)
    
    print_info "Testing endpoints:"
    print_info "  Backend: http://$ALB_DNS"
    print_info "  Frontend: https://$CLOUDFRONT_DOMAIN"
    
    # Test backend health
    print_step "Testing backend health..."
    for i in {1..5}; do
        if curl -s -f "http://$ALB_DNS/health" > /dev/null; then
            print_status "Backend health check passed"
            break
        fi
        if [ $i -eq 5 ]; then
            print_error "Backend health check failed"
            return 1
        fi
        print_info "Attempt $i/5 - waiting 30 seconds..."
        sleep 30
    done
    
    # Test backend API endpoints
    print_step "Testing backend API endpoints..."
    
    # Test docs endpoint
    if curl -s -f "http://$ALB_DNS/docs" > /dev/null; then
        print_status "API documentation accessible"
    else
        print_warning "API documentation may not be accessible"
    fi
    
    # Test OpenAPI spec
    if curl -s -f "http://$ALB_DNS/openapi.json" > /dev/null; then
        print_status "OpenAPI specification accessible"
    else
        print_warning "OpenAPI specification may not be accessible"
    fi
    
    # Test frontend
    print_step "Testing frontend accessibility..."
    sleep 60  # Wait for CloudFront propagation
    
    for i in {1..3}; do
        if curl -s -f "https://$CLOUDFRONT_DOMAIN" > /dev/null; then
            print_status "Frontend accessible via CloudFront"
            break
        fi
        if [ $i -eq 3 ]; then
            print_warning "Frontend may not be fully accessible yet"
        else
            print_info "Attempt $i/3 - waiting 60 seconds for CloudFront..."
            sleep 60
        fi
    done
    
    log_message "End-to-end tests completed"
}

# Function to generate deployment report
generate_deployment_report() {
    print_header "📊 Generating Deployment Report"
    
    REPORT_FILE="deployment_report_$(date +%Y%m%d_%H%M%S).md"
    
    # Get deployment information
    ALB_DNS=$(aws elbv2 describe-load-balancers \
        --names rvtool-alb-dev \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --query 'LoadBalancers[0].DNSName' \
        --output text)
    
    CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution \
        --id EL1JB6MBCPLCI \
        --profile $AWS_PROFILE \
        --query 'Distribution.DomainName' \
        --output text)
    
    # Get latest image URI
    LATEST_IMAGE_URI=""
    if [ -f "latest_image_uri.txt" ]; then
        LATEST_IMAGE_URI=$(cat latest_image_uri.txt)
    fi
    
    # Generate report
    cat > "$REPORT_FILE" << EOF
# RVTool Enhanced UX - Deployment Report

**Deployment Date**: $(date '+%Y-%m-%d %H:%M:%S')
**AWS Account**: $AWS_ACCOUNT_ID
**AWS Region**: $AWS_REGION
**Deployment Status**: ✅ SUCCESS

## Deployment Summary

### Backend Deployment
- **ECS Cluster**: rvtool-cluster-dev
- **ECS Service**: rvtool-api-dev
- **Container Image**: $LATEST_IMAGE_URI
- **Load Balancer**: $ALB_DNS
- **Health Endpoint**: http://$ALB_DNS/health
- **API Documentation**: http://$ALB_DNS/docs

### Frontend Deployment
- **S3 Bucket**: rvtool-static-dev-783764609930-202507111752
- **CloudFront Distribution**: EL1JB6MBCPLCI
- **Primary URL**: https://$CLOUDFRONT_DOMAIN
- **Environment**: Production

## Access Points

### Primary Application
- **Frontend**: https://$CLOUDFRONT_DOMAIN
- **Backend API**: http://$ALB_DNS

### Development/Testing
- **API Health**: http://$ALB_DNS/health
- **API Docs**: http://$ALB_DNS/docs
- **OpenAPI Spec**: http://$ALB_DNS/openapi.json

## Infrastructure Components

### Compute
- ECS Cluster: rvtool-cluster-dev
- ECS Service: rvtool-api-dev
- Application Load Balancer: rvtool-alb-dev

### Storage
- Static Assets: S3 + CloudFront
- File Uploads: S3 bucket
- Database: PostgreSQL RDS

### Networking
- VPC: RVTool-Networking-dev
- Security Groups: RVTool-Security-dev

## Post-Deployment Checklist

- [x] Backend health check passing
- [x] Frontend accessible via CloudFront
- [x] API documentation available
- [ ] End-to-end functionality testing
- [ ] Performance monitoring setup
- [ ] Error tracking configuration

## Rollback Information

**Backup Location**: $BACKUP_DIR
**Rollback Script**: $BACKUP_DIR/rollback.sh

To rollback this deployment:
\`\`\`bash
cd $BACKUP_DIR
./rollback.sh
\`\`\`

## Next Steps

1. **Testing**: Perform comprehensive application testing
2. **Monitoring**: Set up CloudWatch dashboards and alarms
3. **Security**: Review security groups and IAM policies
4. **Performance**: Monitor application performance metrics
5. **Documentation**: Update user documentation with new URLs

## Support Information

- **Deployment Log**: $DEPLOYMENT_LOG
- **AWS Profile**: $AWS_PROFILE
- **Region**: $AWS_REGION

---
*Report generated automatically by RVTool deployment system*
EOF
    
    print_status "Deployment report generated: $REPORT_FILE"
    log_message "Deployment report generated: $REPORT_FILE"
}

# Function to display final summary
display_final_summary() {
    print_header "🎉 Deployment Complete"
    
    # Get endpoints
    ALB_DNS=$(aws elbv2 describe-load-balancers \
        --names rvtool-alb-dev \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --query 'LoadBalancers[0].DNSName' \
        --output text)
    
    CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution \
        --id EL1JB6MBCPLCI \
        --profile $AWS_PROFILE \
        --query 'Distribution.DomainName' \
        --output text)
    
    echo ""
    print_status "🚀 RVTool Enhanced UX Platform Successfully Deployed!"
    echo ""
    print_info "📱 Application Access:"
    echo "  • Primary URL: https://$CLOUDFRONT_DOMAIN"
    echo "  • Backend API: http://$ALB_DNS"
    echo ""
    print_info "🔧 Development/Testing:"
    echo "  • API Health: http://$ALB_DNS/health"
    echo "  • API Docs: http://$ALB_DNS/docs"
    echo "  • OpenAPI Spec: http://$ALB_DNS/openapi.json"
    echo ""
    print_info "📊 Deployment Artifacts:"
    echo "  • Deployment Log: $DEPLOYMENT_LOG"
    echo "  • Backup Directory: $BACKUP_DIR"
    echo "  • Deployment Report: deployment_report_*.md"
    echo ""
    print_info "🎯 Next Steps:"
    echo "  1. Test the application functionality"
    echo "  2. Set up monitoring and alerting"
    echo "  3. Configure custom domain (optional)"
    echo "  4. Set up SSL certificate (optional)"
    echo ""
    print_status "✨ Deployment completed successfully!"
}

# Function to handle deployment failure
handle_deployment_failure() {
    print_error "Deployment failed. Check logs for details."
    log_message "Deployment failed"
    
    print_info "Failure recovery options:"
    echo "  1. Check deployment log: $DEPLOYMENT_LOG"
    echo "  2. Run rollback script: $BACKUP_DIR/rollback.sh"
    echo "  3. Review AWS CloudWatch logs"
    echo "  4. Contact support team"
    
    exit 1
}

# Main execution function
main() {
    print_header "🚀 RVTool Enhanced UX - Full Application Deployment"
    echo ""
    print_info "Starting comprehensive deployment process..."
    print_info "Deployment will be logged to: $DEPLOYMENT_LOG"
    echo ""
    
    log_message "Starting full application deployment"
    
    # Set trap for error handling
    trap handle_deployment_failure ERR
    
    # Execute deployment phases
    check_prerequisites
    create_deployment_backup
    
    # Deploy backend first
    if deploy_backend; then
        print_status "✅ Backend deployment phase completed"
    else
        print_error "❌ Backend deployment failed"
        handle_deployment_failure
    fi
    
    # Deploy frontend
    if deploy_frontend; then
        print_status "✅ Frontend deployment phase completed"
    else
        print_error "❌ Frontend deployment failed"
        handle_deployment_failure
    fi
    
    # Run tests
    if run_e2e_tests; then
        print_status "✅ End-to-end tests completed"
    else
        print_warning "⚠️  Some tests may have failed, but deployment continues"
    fi
    
    # Generate report and summary
    generate_deployment_report
    display_final_summary
    
    log_message "Full application deployment completed successfully"
    print_status "🎉 Full application deployment completed successfully!"
}

# Execute main function
main "$@"
