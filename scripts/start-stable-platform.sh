#!/bin/bash

# RVTool Platform Startup Script - STABLE VERSION (No Reload)
# Starts both frontend and backend without reload for stable connections
# Version: 2.1 - Connection Stability Fix

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
BACKEND_PORT=8000
FRONTEND_PORT=3000
PROJECT_ROOT="/home/ubuntu/rvtool"
BACKEND_DIR="$PROJECT_ROOT/enhanced-ux/backend"
FRONTEND_DIR="$PROJECT_ROOT/enhanced-ux/frontend"

# Function to print colored output
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

print_fix() {
    echo -e "${CYAN}🔧 $1${NC}"
}

# Function to stop existing services
stop_existing_services() {
    print_info "Stopping existing services..."
    
    # Stop backend processes (all variations)
    pkill -f "app_enhanced" 2>/dev/null || true
    pkill -f "uvicorn.*app_enhanced" 2>/dev/null || true
    pkill -f "uvicorn.*8000" 2>/dev/null || true
    
    # Stop frontend processes
    pkill -f "vite.*3000" 2>/dev/null || true
    pkill -f "npm.*dev" 2>/dev/null || true
    pkill -f "node.*vite.*3000" 2>/dev/null || true
    
    # Wait for processes to stop
    sleep 3
    
    # Force kill if still running
    if ss -tlnp | grep -q ":$BACKEND_PORT"; then
        print_warning "Port $BACKEND_PORT still in use. Force killing..."
        fuser -k $BACKEND_PORT/tcp 2>/dev/null || true
        sleep 2
    fi
    
    if ss -tlnp | grep -q ":$FRONTEND_PORT"; then
        print_warning "Port $FRONTEND_PORT still in use. Force killing..."
        fuser -k $FRONTEND_PORT/tcp 2>/dev/null || true
        sleep 2
    fi
    
    print_status "Existing services stopped"
}

# Function to start backend (STABLE - No Reload)
start_backend_stable() {
    print_info "🚀 Starting Backend (STABLE MODE - No Reload)"
    
    cd "$BACKEND_DIR"
    
    print_fix "Starting backend in stable mode (no auto-reload)..."
    print_info "Backend will be accessible on: http://localhost:$BACKEND_PORT"
    
    # Start backend WITHOUT --reload for stability
    nohup python3 -m uvicorn app_enhanced:app \
        --host 0.0.0.0 \
        --port $BACKEND_PORT \
        --log-level info \
        > backend_stable.log 2>&1 &
    
    BACKEND_PID=$!
    echo $BACKEND_PID > backend_stable.pid
    
    # Wait for backend to start
    print_info "Waiting for backend to initialize..."
    for i in {1..30}; do
        if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
            print_status "Backend started successfully (STABLE MODE)"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Backend failed to start within 30 seconds"
            print_info "Check backend_stable.log for errors:"
            tail -10 backend_stable.log
            exit 1
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    
    # Test backend endpoints
    print_info "Testing backend endpoints..."
    if curl -s http://localhost:$BACKEND_PORT/api/health | grep -q "healthy"; then
        print_status "Backend health check passed"
    else
        print_warning "Backend health check unclear"
    fi
    
    if curl -s http://localhost:$BACKEND_PORT/api/cleaning/health > /dev/null 2>&1; then
        print_status "Cleaning endpoints accessible"
    else
        print_warning "Cleaning endpoints may not be accessible"
    fi
}

# Function to start frontend
start_frontend_stable() {
    print_info "🌐 Starting Frontend"
    
    cd "$FRONTEND_DIR"
    
    # Ensure environment is set correctly
    if [ ! -f ".env.development" ]; then
        print_error "Frontend .env.development not found"
        exit 1
    fi
    
    # Check environment configuration
    if grep -q "localhost:8000" .env.development; then
        print_status "Frontend configured for local backend"
    else
        print_warning "Frontend may not be configured for local backend"
    fi
    
    print_fix "Starting frontend..."
    print_info "Frontend will be accessible on: http://localhost:$FRONTEND_PORT"
    
    # Start frontend
    nohup npm run dev -- --host 0.0.0.0 --port $FRONTEND_PORT > frontend_stable.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > frontend_stable.pid
    
    # Wait for frontend to start
    print_info "Waiting for frontend to build and start..."
    for i in {1..45}; do
        if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
            print_status "Frontend started successfully"
            break
        fi
        if [ $i -eq 45 ]; then
            print_warning "Frontend taking longer than expected to start"
            break
        fi
        sleep 1
        if [ $((i % 5)) -eq 0 ]; then
            echo -n " [$i/45]"
        else
            echo -n "."
        fi
    done
    echo ""
}

# Function to test connection
test_connection() {
    print_info "🧪 Testing Backend-Frontend Connection"
    
    # Test backend directly
    print_info "Testing backend endpoints..."
    
    if curl -s http://localhost:8000/api/health | grep -q "healthy"; then
        print_status "✅ Backend health: OK"
    else
        print_error "❌ Backend health: FAILED"
        return 1
    fi
    
    if curl -s -X POST http://localhost:8000/api/cleaning/upload -H "Content-Type: application/json" -d '{}' | grep -q "field required"; then
        print_status "✅ Cleaning upload endpoint: OK (expects file)"
    else
        print_error "❌ Cleaning upload endpoint: FAILED"
        return 1
    fi
    
    # Test CORS
    if curl -s -H "Origin: http://localhost:3000" http://localhost:8000/api/health | grep -q "healthy"; then
        print_status "✅ CORS configuration: OK"
    else
        print_warning "⚠️  CORS configuration: May have issues"
    fi
    
    print_status "🎉 Connection tests completed successfully!"
}

# Main execution
main() {
    case "${1:-start}" in
        "start")
            print_info "🔧 RVTool Platform - STABLE CONNECTION MODE"
            echo ""
            
            stop_existing_services
            start_backend_stable
            
            if [ $? -eq 0 ]; then
                start_frontend_stable
                test_connection
                
                echo ""
                print_status "🚀 STABLE PLATFORM READY!"
                print_info "Frontend: http://localhost:3000"
                print_info "Backend: http://localhost:8000"
                print_info "API Docs: http://localhost:8000/api/docs"
                echo ""
                print_fix "Backend running in STABLE mode (no auto-reload)"
                print_fix "This should resolve connection refused errors"
                echo ""
                print_info "Log files:"
                print_info "• Backend: $BACKEND_DIR/backend_stable.log"
                print_info "• Frontend: $FRONTEND_DIR/frontend_stable.log"
            else
                print_error "Backend failed to start. Not starting frontend."
                exit 1
            fi
            ;;
        "stop")
            print_info "Stopping stable platform..."
            stop_existing_services
            print_status "Platform stopped"
            ;;
        "test")
            test_connection
            ;;
        *)
            echo "Usage: $0 {start|stop|test}"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
