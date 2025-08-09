#!/bin/bash

# Enhanced UX Frontend Startup Script
# Starts the React frontend with proper backend connectivity

echo "🚀 Starting Enhanced UX Migration Analysis Platform..."
echo "=================================================="

# Change to frontend directory
cd /home/ubuntu/rvtool/enhanced-ux/frontend

# Check if Node.js and npm are available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install npm"
    exit 1
fi

echo "📦 Node.js version: $(node --version)"
echo "📦 npm version: $(npm --version)"

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📥 Installing frontend dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
fi

# Stop any existing frontend processes
echo "🛑 Stopping existing frontend processes..."
pkill -f "npm run dev" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 2

# Check backend connectivity
echo "🔧 Checking backend connectivity..."
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health)

if [ "$BACKEND_STATUS" != "200" ]; then
    echo "⚠️  Backend not responding on port 8001"
    echo "   Starting enhanced backend..."
    cd /home/ubuntu/rvtool/enhanced-ux/backend
    nohup python3 enhanced_test_app.py > enhanced_backend.log 2>&1 &
    sleep 5
    cd /home/ubuntu/rvtool/enhanced-ux/frontend
    
    # Check again
    BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health)
    if [ "$BACKEND_STATUS" != "200" ]; then
        echo "❌ Failed to start backend. Please check backend logs."
        exit 1
    fi
fi

echo "✅ Backend is healthy"

# Start the frontend development server
echo "🌐 Starting frontend development server..."
echo "   Frontend will be available at: http://localhost:3000"
echo "   Backend API available at: http://localhost:8001"
echo ""
echo "🎯 Features Available:"
echo "   • Real RVTools.xlsx file processing"
echo "   • 4-phase migration analysis workflow"
echo "   • Session management"
echo "   • Migration scope analysis"
echo "   • Cost estimates"
echo "   • Modernization opportunities"
echo ""
echo "📝 To stop the server: Press Ctrl+C or run 'pkill -f vite'"
echo "=================================================="

# Start in foreground so user can see logs and stop with Ctrl+C
npm run dev
