#!/bin/bash

# Deploy Frontend Assets to S3 and Invalidate CloudFront
# Uses AWS CLI with smartslot profile

set -e

# Configuration
AWS_PROFILE="smartslot"
AWS_REGION="us-east-1"
PROJECT_NAME="rvtool-enhanced"
ENVIRONMENT="prod"
S3_BUCKET="rvtool-enhanced-prod-frontend-783764609930"
CLOUDFRONT_DISTRIBUTION_ID="ELYMX4LVZ7UPV"

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
FRONTEND_DIR="$PROJECT_ROOT/frontend"

print_info "Deploying frontend assets to S3..."
print_info "Project root: $PROJECT_ROOT"
print_info "Frontend directory: $FRONTEND_DIR"

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    print_error "Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi

cd "$FRONTEND_DIR"

# Check if package.json exists
if [ ! -f "package.json" ]; then
    print_warning "package.json not found. Creating basic React app structure..."
    
    # Create basic package.json
    cat > package.json << 'EOF'
{
  "name": "rvtool-enhanced-frontend",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.8.0",
    "axios": "^1.3.0",
    "@headlessui/react": "^1.7.0",
    "@heroicons/react": "^2.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0",
    "@vitejs/plugin-react": "^3.1.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.2.0",
    "typescript": "^4.9.0",
    "vite": "^4.1.0"
  }
}
EOF
    
    # Create basic index.html
    mkdir -p public
    cat > public/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>RVTool Enhanced UX</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
EOF
    
    # Create basic src structure
    mkdir -p src
    cat > src/main.tsx << 'EOF'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
EOF
    
    cat > src/App.tsx << 'EOF'
import React from 'react'

function App() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="max-w-md mx-auto bg-white rounded-xl shadow-md overflow-hidden">
        <div className="p-8">
          <div className="uppercase tracking-wide text-sm text-indigo-500 font-semibold">
            RVTool Enhanced UX
          </div>
          <h1 className="block mt-1 text-lg leading-tight font-medium text-black">
            Welcome to RVTool Enhanced UX Platform
          </h1>
          <p className="mt-2 text-gray-500">
            AI-powered platform for analyzing VMware RVTools exports and providing 
            AWS migration cost optimization recommendations.
          </p>
          <div className="mt-4">
            <button className="bg-indigo-500 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded">
              Get Started
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
EOF
    
    cat > src/index.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
EOF
    
    # Create vite config
    cat > vite.config.ts << 'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    assetsDir: 'static'
  }
})
EOF
    
    # Create tailwind config
    cat > tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOF
    
    print_status "Created basic React app structure"
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    print_info "Installing dependencies..."
    npm install
    print_status "Dependencies installed"
fi

# Build the frontend
print_info "Building frontend application..."
npm run build

if [ $? -eq 0 ]; then
    print_status "Frontend build completed"
else
    print_error "Frontend build failed"
    exit 1
fi

# Check if dist directory exists
if [ ! -d "dist" ]; then
    print_error "Build output directory 'dist' not found"
    exit 1
fi

# Sync files to S3
print_info "Uploading files to S3 bucket: $S3_BUCKET"
aws s3 sync dist/ s3://$S3_BUCKET/ \
    --profile $AWS_PROFILE \
    --region $AWS_REGION \
    --delete \
    --cache-control "public, max-age=31536000" \
    --exclude "*.html" \
    --exclude "service-worker.js"

# Upload HTML files with no-cache
aws s3 sync dist/ s3://$S3_BUCKET/ \
    --profile $AWS_PROFILE \
    --region $AWS_REGION \
    --cache-control "no-cache, no-store, must-revalidate" \
    --include "*.html" \
    --include "service-worker.js"

if [ $? -eq 0 ]; then
    print_status "Files uploaded to S3 successfully"
else
    print_error "S3 upload failed"
    exit 1
fi

# Create CloudFront invalidation
print_info "Creating CloudFront invalidation..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
    --paths "/*" \
    --profile $AWS_PROFILE \
    --query 'Invalidation.Id' \
    --output text)

if [ $? -eq 0 ]; then
    print_status "CloudFront invalidation created: $INVALIDATION_ID"
    print_info "Waiting for invalidation to complete..."
    
    aws cloudfront wait invalidation-completed \
        --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
        --id $INVALIDATION_ID \
        --profile $AWS_PROFILE
    
    print_status "CloudFront invalidation completed"
else
    print_warning "CloudFront invalidation failed, but files are uploaded"
fi

print_status "Frontend deployment completed!"
print_info "🌐 Frontend URL: https://d399osit04h299.cloudfront.net"
print_info "📝 Note: It may take a few minutes for changes to propagate globally"

# Clean up build directory to save space
print_info "Cleaning up build directory..."
rm -rf dist/

print_status "Frontend asset deployment completed!"
