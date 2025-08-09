#!/bin/bash

# Start Enhanced Frontend with AWS Backend Configuration
set -e

echo "🚀 Starting Enhanced Frontend with AWS Backend Integration..."

cd /home/ubuntu/rvtool/enhanced-ux/frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start development server with AWS configuration
echo "🌐 Starting frontend with AWS backend proxy..."
echo "Frontend will be available at: http://localhost:3000"
echo "API calls will be proxied to: http://rvtool-alb-dev-1648331028.us-east-1.elb.amazonaws.com"

# Start with AWS environment
npm run dev:aws
