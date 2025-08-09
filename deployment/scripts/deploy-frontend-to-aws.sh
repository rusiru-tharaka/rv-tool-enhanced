#!/bin/bash

# RVTool Enhanced Frontend Deployment Script
# Deploys the React/Vite frontend to AWS S3 + CloudFront
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
FRONTEND_DIR="./frontend"
S3_BUCKET="rvtool-static-dev-783764609930-202507111752"
CLOUDFRONT_DISTRIBUTION_ID="EL1JB6MBCPLCI"

# Get ALB DNS for API endpoint
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --names rvtool-alb-dev \
    --profile $AWS_PROFILE \
    --region $AWS_REGION \
    --query 'LoadBalancers[0].DNSName' \
    --output text 2>/dev/null || echo "rvtool-alb-dev-1648331028.us-east-1.elb.amazonaws.com")

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
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js not found. Please install Node.js 18+."
        exit 1
    fi
    print_status "Node.js available: $(node --version)"
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        print_error "npm not found. Please install npm."
        exit 1
    fi
    print_status "npm available: $(npm --version)"
    
    # Check AWS credentials
    if ! aws sts get-caller-identity --profile $AWS_PROFILE &> /dev/null; then
        print_error "AWS credentials not configured for profile: $AWS_PROFILE"
        exit 1
    fi
    print_status "AWS credentials configured"
    
    # Check frontend directory
    if [ ! -d "$FRONTEND_DIR" ]; then
        print_error "Frontend directory not found: $FRONTEND_DIR"
        exit 1
    fi
    print_status "Frontend directory found"
    
    # Check package.json
    if [ ! -f "$FRONTEND_DIR/package.json" ]; then
        print_error "package.json not found in: $FRONTEND_DIR"
        exit 1
    fi
    print_status "package.json found"
    
    print_info "S3 Bucket: $S3_BUCKET"
    print_info "CloudFront Distribution: $CLOUDFRONT_DISTRIBUTION_ID"
    print_info "API Endpoint: http://$ALB_DNS"
}

# Function to setup production environment
setup_production_environment() {
    print_header "⚙️  Setting Up Production Environment"
    
    cd "$FRONTEND_DIR"
    
    # Create production environment file
    print_step "Creating production environment configuration..."
    cat > .env.production << EOF
# Production Environment Configuration - AWS Deployment
VITE_API_BASE_URL=http://$ALB_DNS
VITE_ALLOWED_HOSTS=$ALB_DNS,*.elb.amazonaws.com,*.amazonaws.com,localhost,127.0.0.1
VITE_APP_TITLE=RVTool Migration Analysis Platform
VITE_APP_VERSION=2.0.0-production
VITE_ENVIRONMENT=production
VITE_AWS_REGION=us-east-1
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_ERROR_REPORTING=true
EOF
    print_status "Production environment configured"
    
    # Update vite.config.ts for production
    print_step "Updating Vite configuration for production..."
    if [ ! -f "vite.config.ts.backup" ]; then
        cp vite.config.ts vite.config.ts.backup
    fi
    
    cat > vite.config.ts << 'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'terser',
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          utils: ['axios', 'lodash']
        }
      }
    },
    chunkSizeWarningLimit: 1000
  },
  server: {
    port: 3000,
    host: '0.0.0.0'
  },
  preview: {
    port: 3000,
    host: '0.0.0.0'
  },
  define: {
    'process.env.NODE_ENV': JSON.stringify('production')
  }
})
EOF
    print_status "Vite configuration updated"
    
    cd ..
}

# Function to install dependencies and build
build_application() {
    print_header "🏗️  Building Frontend Application"
    
    cd "$FRONTEND_DIR"
    
    # Install dependencies
    print_step "Installing dependencies..."
    npm ci --production=false
    print_status "Dependencies installed"
    
    # Run build
    print_step "Building application for production..."
    NODE_ENV=production npm run build
    print_status "Application built successfully"
    
    # Verify build output
    if [ ! -d "dist" ]; then
        print_error "Build output directory 'dist' not found"
        exit 1
    fi
    
    BUILD_SIZE=$(du -sh dist | cut -f1)
    print_info "Build size: $BUILD_SIZE"
    
    # List build contents
    print_info "Build contents:"
    ls -la dist/
    
    cd ..
}

# Function to deploy to S3
deploy_to_s3() {
    print_header "☁️  Deploying to S3"
    
    cd "$FRONTEND_DIR"
    
    # Sync files to S3
    print_step "Uploading files to S3 bucket: $S3_BUCKET"
    aws s3 sync dist/ s3://$S3_BUCKET/ \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --delete \
        --cache-control "public, max-age=31536000" \
        --exclude "*.html" \
        --exclude "*.json"
    
    # Upload HTML files with different cache settings
    print_step "Uploading HTML files with no-cache headers..."
    aws s3 sync dist/ s3://$S3_BUCKET/ \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --cache-control "no-cache, no-store, must-revalidate" \
        --include "*.html" \
        --include "*.json"
    
    print_status "Files uploaded to S3"
    
    # Set bucket website configuration
    print_step "Configuring S3 bucket for static website hosting..."
    aws s3 website s3://$S3_BUCKET \
        --index-document index.html \
        --error-document index.html \
        --profile $AWS_PROFILE \
        --region $AWS_REGION
    
    print_status "S3 website configuration updated"
    
    cd ..
}

# Function to invalidate CloudFront cache
invalidate_cloudfront() {
    print_header "🔄 Invalidating CloudFront Cache"
    
    print_step "Creating CloudFront invalidation..."
    INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
        --paths "/*" \
        --profile $AWS_PROFILE \
        --query 'Invalidation.Id' \
        --output text)
    
    print_status "Invalidation created: $INVALIDATION_ID"
    
    print_step "Waiting for invalidation to complete..."
    aws cloudfront wait invalidation-completed \
        --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
        --id $INVALIDATION_ID \
        --profile $AWS_PROFILE
    
    print_status "CloudFront cache invalidated"
}

# Function to get CloudFront domain
get_cloudfront_domain() {
    CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution \
        --id $CLOUDFRONT_DISTRIBUTION_ID \
        --profile $AWS_PROFILE \
        --query 'Distribution.DomainName' \
        --output text)
    
    export CLOUDFRONT_DOMAIN
}

# Function to verify deployment
verify_deployment() {
    print_header "✅ Verifying Deployment"
    
    get_cloudfront_domain
    
    print_info "CloudFront Domain: $CLOUDFRONT_DOMAIN"
    
    # Test CloudFront endpoint
    print_step "Testing CloudFront endpoint..."
    sleep 60  # Wait for CloudFront to propagate
    
    for i in {1..5}; do
        if curl -s -f "https://$CLOUDFRONT_DOMAIN" > /dev/null; then
            print_status "CloudFront endpoint accessible"
            break
        fi
        if [ $i -eq 5 ]; then
            print_warning "CloudFront endpoint test failed after 5 attempts"
        else
            print_info "Attempt $i/5 - waiting 30 seconds..."
            sleep 30
        fi
    done
    
    # Test S3 direct access
    print_step "Testing S3 direct access..."
    S3_WEBSITE_URL="http://$S3_BUCKET.s3-website-$AWS_REGION.amazonaws.com"
    if curl -s -f "$S3_WEBSITE_URL" > /dev/null; then
        print_status "S3 website endpoint accessible"
    else
        print_warning "S3 website endpoint may not be accessible"
    fi
    
    print_info "S3 Website URL: $S3_WEBSITE_URL"
}

# Function to run post-deployment tests
run_post_deployment_tests() {
    print_header "🧪 Running Post-Deployment Tests"
    
    get_cloudfront_domain
    
    # Test main page
    print_step "Testing main application page..."
    MAIN_PAGE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$CLOUDFRONT_DOMAIN")
    if [ "$MAIN_PAGE_STATUS" = "200" ]; then
        print_status "Main page loads successfully"
    else
        print_warning "Main page returned status: $MAIN_PAGE_STATUS"
    fi
    
    # Test API connectivity from frontend
    print_step "Testing API connectivity..."
    API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$ALB_DNS/health")
    if [ "$API_STATUS" = "200" ]; then
        print_status "API endpoint accessible from frontend"
    else
        print_warning "API endpoint returned status: $API_STATUS"
    fi
    
    # Check for common assets
    print_step "Checking for static assets..."
    ASSETS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$CLOUDFRONT_DOMAIN/assets/")
    if [ "$ASSETS_STATUS" = "200" ] || [ "$ASSETS_STATUS" = "403" ]; then
        print_status "Static assets directory accessible"
    else
        print_info "Assets status: $ASSETS_STATUS"
    fi
}

# Function to display deployment summary
display_summary() {
    print_header "🎉 Frontend Deployment Summary"
    
    get_cloudfront_domain
    
    echo ""
    print_status "✅ Frontend deployment completed successfully!"
    echo ""
    print_info "📊 Deployment Details:"
    echo "  • S3 Bucket: $S3_BUCKET"
    echo "  • CloudFront Distribution: $CLOUDFRONT_DISTRIBUTION_ID"
    echo "  • API Endpoint: http://$ALB_DNS"
    echo ""
    print_info "🌐 Access Points:"
    echo "  • Primary URL: https://$CLOUDFRONT_DOMAIN"
    echo "  • S3 Direct: http://$S3_BUCKET.s3-website-$AWS_REGION.amazonaws.com"
    echo ""
    print_info "🔧 Configuration:"
    echo "  • Environment: Production"
    echo "  • API Base URL: http://$ALB_DNS"
    echo "  • Build Size: $(du -sh $FRONTEND_DIR/dist | cut -f1)"
    echo ""
    print_info "📋 Next Steps:"
    echo "  1. Test the full application functionality"
    echo "  2. Monitor CloudFront metrics"
    echo "  3. Set up custom domain (optional)"
    echo "  4. Configure SSL certificate (optional)"
    echo ""
}

# Function to cleanup on failure
cleanup_on_failure() {
    print_error "Frontend deployment failed. Cleaning up..."
    
    cd "$FRONTEND_DIR"
    
    # Restore original vite config if backup exists
    if [ -f "vite.config.ts.backup" ]; then
        mv vite.config.ts.backup vite.config.ts
        print_info "Restored original Vite configuration"
    fi
    
    # Remove production env file
    if [ -f ".env.production" ]; then
        rm .env.production
        print_info "Removed production environment file"
    fi
    
    cd ..
}

# Main execution function
main() {
    print_header "🚀 RVTool Enhanced Frontend Deployment"
    echo ""
    print_info "Starting frontend deployment process..."
    echo ""
    
    # Set trap for error handling
    trap cleanup_on_failure ERR
    
    # Execute deployment steps
    check_prerequisites
    setup_production_environment
    build_application
    deploy_to_s3
    invalidate_cloudfront
    verify_deployment
    run_post_deployment_tests
    display_summary
    
    print_status "🎉 Frontend deployment completed successfully!"
}

# Execute main function
main "$@"
