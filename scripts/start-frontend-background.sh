#!/bin/bash

# Enhanced UX Frontend Background Startup Script
# Starts both backend and frontend in background

echo "🚀 Starting Enhanced UX Platform in Background..."
echo "=============================================="

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Start Backend (if not already running)
if ! check_port 8001; then
    echo "🔧 Starting Enhanced Backend..."
    cd /home/ubuntu/rvtool/enhanced-ux/backend
    nohup python3 enhanced_test_app.py > enhanced_backend.log 2>&1 &
    sleep 3
    
    if check_port 8001; then
        echo "✅ Backend started successfully on port 8001"
    else
        echo "❌ Failed to start backend"
        exit 1
    fi
else
    echo "✅ Backend already running on port 8001"
fi

# Start Frontend (if not already running)
if ! check_port 3000; then
    echo "🌐 Starting Enhanced Frontend..."
    cd /home/ubuntu/rvtool/enhanced-ux/frontend
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "📥 Installing dependencies..."
        npm install
    fi
    
    nohup npm run dev > frontend.log 2>&1 &
    sleep 5
    
    if check_port 3000; then
        echo "✅ Frontend started successfully on port 3000"
    else
        echo "❌ Failed to start frontend"
        exit 1
    fi
else
    echo "✅ Frontend already running on port 3000"
fi

# Verify integration
echo ""
echo "🔗 Testing Integration..."
sleep 2

FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/)
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health)

if [ "$FRONTEND_STATUS" = "200" ] && [ "$BACKEND_STATUS" = "200" ]; then
    echo "✅ Integration successful!"
    echo ""
    echo "🎉 Enhanced UX Platform is now running:"
    echo "   🌐 Frontend: http://localhost:3000"
    echo "   🔧 Backend:  http://localhost:8001"
    echo "   📚 API Docs: http://localhost:8001/api/docs"
    echo ""
    echo "🎯 Ready for:"
    echo "   • RVTools.xlsx file uploads"
    echo "   • Real VM inventory processing (tested with 1,028 VMs)"
    echo "   • 4-phase migration analysis"
    echo "   • Session management"
    echo ""
    echo "📝 To stop services:"
    echo "   pkill -f 'npm run dev'"
    echo "   pkill -f 'enhanced_test_app'"
else
    echo "❌ Integration failed"
    echo "   Frontend status: $FRONTEND_STATUS"
    echo "   Backend status: $BACKEND_STATUS"
    exit 1
fi
