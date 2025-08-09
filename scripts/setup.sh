#!/bin/bash

# RVTool Enhanced UX - Setup Script
# Sets up the development environment

set -e

echo "🚀 Setting up RVTool Enhanced UX Platform..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check prerequisites
print_info "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

print_status "Prerequisites check passed"

# Setup backend
print_info "Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
fi

print_info "Activating virtual environment and installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

print_status "Backend setup completed"

# Setup frontend
print_info "Setting up frontend..."
cd ../frontend

print_info "Installing Node.js dependencies..."
npm install

print_status "Frontend setup completed"

# Create environment files if they don't exist
cd ..

if [ ! -f "backend/.env" ]; then
    print_info "Creating backend .env file..."
    cat > backend/.env << EOF
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/rvtool_db

# AWS Configuration
AWS_DEFAULT_REGION=us-east-1

# Application Configuration
LOG_LEVEL=info
ENVIRONMENT=development
EOF
fi

if [ ! -f "frontend/.env.local" ]; then
    print_info "Creating frontend .env.local file..."
    cat > frontend/.env.local << EOF
# Backend API URL
VITE_API_URL=http://localhost:8000

# Environment
VITE_ENVIRONMENT=development
EOF
fi

print_status "🎉 Setup completed successfully!"
print_info "Next steps:"
echo "  1. Configure your database connection in backend/.env"
echo "  2. Run './scripts/start-dev.sh' to start the development servers"
echo "  3. Access the application at http://localhost:5173"
