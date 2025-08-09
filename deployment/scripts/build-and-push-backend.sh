#!/bin/bash

# Build and Push Backend Docker Image to ECR
# Uses AWS CLI with smartslot profile

set -e

# Configuration
AWS_PROFILE="smartslot"
AWS_REGION="us-east-1"
PROJECT_NAME="rvtool-enhanced"
ENVIRONMENT="prod"
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

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

print_info "Building and pushing backend Docker image..."
print_info "Project root: $PROJECT_ROOT"
print_info "Backend directory: $BACKEND_DIR"

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    print_error "Backend directory not found: $BACKEND_DIR"
    exit 1
fi

# Check if Dockerfile exists
if [ ! -f "$BACKEND_DIR/Dockerfile" ]; then
    print_warning "Dockerfile not found in backend directory. Creating a basic one..."
    
    # Create a basic Dockerfile
    cat > "$BACKEND_DIR/Dockerfile" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
    
    print_status "Created basic Dockerfile"
fi

# Check if requirements.txt exists
if [ ! -f "$BACKEND_DIR/requirements.txt" ]; then
    print_warning "requirements.txt not found. Creating basic one..."
    
    cat > "$BACKEND_DIR/requirements.txt" << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
sqlalchemy==2.0.23
alembic==1.13.0
psycopg2-binary==2.9.9
redis==5.0.1
boto3==1.34.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
pandas==2.1.4
openpyxl==3.1.2
requests==2.31.0
EOF
    
    print_status "Created basic requirements.txt"
fi

# Login to ECR
print_info "Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION --profile $AWS_PROFILE | \
    docker login --username AWS --password-stdin $ECR_REPOSITORY

if [ $? -eq 0 ]; then
    print_status "ECR login successful"
else
    print_error "ECR login failed"
    exit 1
fi

# Build Docker image
print_info "Building Docker image..."
cd "$BACKEND_DIR"

docker build -t $PROJECT_NAME-backend:latest .

if [ $? -eq 0 ]; then
    print_status "Docker image built successfully"
else
    print_error "Docker image build failed"
    exit 1
fi

# Tag image for ECR
print_info "Tagging image for ECR..."
docker tag $PROJECT_NAME-backend:latest $ECR_REPOSITORY:latest
docker tag $PROJECT_NAME-backend:latest $ECR_REPOSITORY:$(date +%Y%m%d-%H%M%S)

# Push image to ECR
print_info "Pushing image to ECR..."
docker push $ECR_REPOSITORY:latest
docker push $ECR_REPOSITORY:$(date +%Y%m%d-%H%M%S)

if [ $? -eq 0 ]; then
    print_status "Docker image pushed successfully to ECR!"
    print_info "🐳 Image URI: $ECR_REPOSITORY:latest"
else
    print_error "Docker image push failed"
    exit 1
fi

# Clean up local images to save space
print_info "Cleaning up local Docker images..."
docker rmi $PROJECT_NAME-backend:latest 2>/dev/null || true
docker rmi $ECR_REPOSITORY:latest 2>/dev/null || true

print_status "Backend Docker image deployment completed!"
print_info "📋 Next steps:"
print_info "  1. Update ECS service to use the new image"
print_info "  2. Deploy frontend assets to S3"
print_info "  3. Test the complete application"
