#!/bin/bash

# RVTool Enhanced UX - Fixed Network Startup Script
# Improved version with better frontend handling

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
BACKEND_PORT=8001
FRONTEND_PORT=3000
PROJECT_ROOT="/home/ubuntu/rvtool"
BACKEND_DIR="$PROJECT_ROOT/enhanced-ux/backend"
FRONTEND_DIR="$PROJECT_ROOT/enhanced-ux/frontend"
RVTOOL_API_DIR="$PROJECT_ROOT/rvtool-api"

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

print_ai() {
    echo -e "${CYAN}🤖 $1${NC}"
}

# Function to get server IP
get_server_ip() {
    SERVER_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7}' | head -1)
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP=$(hostname -I | awk '{print $1}')
    fi
    if [ -z "$SERVER_IP" ]; then
        SERVER_IP="10.0.7.44"
    fi
    echo "$SERVER_IP"
}

# Function to stop existing services
stop_existing_services() {
    print_info "Stopping existing services..."
    
    # Stop backend processes
    pkill -f "app_enhanced" 2>/dev/null || true
    pkill -f "uvicorn.*8001" 2>/dev/null || true
    
    # Stop frontend processes
    pkill -f "vite" 2>/dev/null || true
    pkill -f "npm.*dev" 2>/dev/null || true
    pkill -f "node.*vite" 2>/dev/null || true
    
    # Wait for processes to stop
    sleep 3
    print_status "Existing services stopped"
}

# Function to start backend
start_backend() {
    print_header "🚀 Starting AI-Enhanced Backend"
    
    cd "$BACKEND_DIR"
    export PYTHONPATH="$RVTOOL_API_DIR:$PYTHONPATH"
    
    print_ai "Starting AI-Enhanced Backend on port $BACKEND_PORT..."
    
    # Start backend
    nohup python3 -m uvicorn app_enhanced:app \
        --host 0.0.0.0 \
        --port $BACKEND_PORT \
        --reload \
        --log-level info \
        > backend_network.log 2>&1 &
    
    BACKEND_PID=$!
    echo $BACKEND_PID > backend.pid
    
    # Wait for backend to start
    print_info "Waiting for backend to initialize..."
    for i in {1..20}; do
        if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
            print_status "Backend started successfully"
            return 0
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    print_error "Backend failed to start"
    return 1
}

# Function to start frontend with improved handling
start_frontend() {
    print_header "🌐 Starting AI-Enhanced Frontend"
    
    cd "$FRONTEND_DIR"
    
    # Ensure package.json has the right scripts
    print_info "Checking package.json scripts..."
    if ! grep -q "dev:network" package.json; then
        print_warning "Adding missing dev:network script..."
        # This should already be fixed, but just in case
        npm run dev -- --host 0.0.0.0 --mode network > frontend_network.log 2>&1 &
    else
        print_info "Starting frontend with dev:network script..."
        npm run dev:network > frontend_network.log 2>&1 &
    fi
    
    FRONTEND_PID=$!
    echo $FRONTEND_PID > frontend.pid
    
    print_info "Waiting for frontend to start (this may take 30-45 seconds)..."
    
    # Wait for frontend with more patience
    for i in {1..60}; do
        # Check if process is still running
        if ! kill -0 $FRONTEND_PID 2>/dev/null; then
            print_error "Frontend process died. Check frontend_network.log"
            return 1
        fi
        
        # Check if frontend is responding
        if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
            print_status "Frontend started successfully"
            return 0
        fi
        
        # Show progress every 5 seconds
        if [ $((i % 5)) -eq 0 ]; then
            echo -n " [$i/60]"
        else
            echo -n "."
        fi
        sleep 1
    done
    
    echo ""
    print_warning "Frontend taking longer than expected"
    print_info "Check frontend_network.log for details"
    
    # Show last few lines of log
    print_info "Last few lines of frontend log:"
    tail -5 frontend_network.log 2>/dev/null || echo "No log file found"
    
    return 1
}

# Function to test services
test_services() {
    print_header "🔍 Testing Services"
    
    # Test backend
    if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        print_status "Backend: HEALTHY"
        BACKEND_OK=true
    else
        print_error "Backend: NOT RESPONDING"
        BACKEND_OK=false
    fi
    
    # Test frontend
    if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
        print_status "Frontend: RUNNING"
        FRONTEND_OK=true
    else
        print_error "Frontend: NOT RESPONDING"
        FRONTEND_OK=false
    fi
    
    # Test network access
    SERVER_IP=$(get_server_ip)
    if curl -s http://$SERVER_IP:$FRONTEND_PORT > /dev/null 2>&1; then
        print_status "Network Access: WORKING"
    else
        print_warning "Network Access: MAY HAVE ISSUES"
    fi
    
    if [ "$BACKEND_OK" = true ] && [ "$FRONTEND_OK" = true ]; then
        return 0
    else
        return 1
    fi
}

# Function to display service info
display_service_info() {
    SERVER_IP=$(get_server_ip)
    
    print_header "🎉 AI-Enhanced Platform Status"
    
    echo ""
    print_ai "SERVICES:"
    print_status "Backend API: http://$SERVER_IP:$BACKEND_PORT"
    print_status "Frontend App: http://$SERVER_IP:$FRONTEND_PORT"
    echo ""
    
    print_info "ACCESS URLS:"
    echo "  • Main Application: http://$SERVER_IP:$FRONTEND_PORT"
    echo "  • API Documentation: http://$SERVER_IP:$BACKEND_PORT/docs"
    echo "  • Health Check: http://$SERVER_IP:$BACKEND_PORT/health"
    echo ""
    
    print_info "LOG FILES:"
    echo "  • Backend: $BACKEND_DIR/backend_network.log"
    echo "  • Frontend: $FRONTEND_DIR/frontend_network.log"
    echo ""
    
    print_warning "TO STOP SERVICES:"
    echo "  $0 stop"
}

# Function to show logs
show_logs() {
    print_header "📋 Service Logs"
    
    echo -e "${BLUE}=== Backend Log (last 10 lines) ===${NC}"
    tail -10 "$BACKEND_DIR/backend_network.log" 2>/dev/null || echo "No backend log found"
    
    echo -e "\n${BLUE}=== Frontend Log (last 10 lines) ===${NC}"
    tail -10 "$FRONTEND_DIR/frontend_network.log" 2>/dev/null || echo "No frontend log found"
}

# Function to stop services
stop_services() {
    print_header "🛑 Stopping Services"
    
    # Stop using PID files
    if [ -f "$BACKEND_DIR/backend.pid" ]; then
        BACKEND_PID=$(cat "$BACKEND_DIR/backend.pid")
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            kill "$BACKEND_PID"
            print_status "Backend stopped"
        fi
        rm -f "$BACKEND_DIR/backend.pid"
    fi
    
    if [ -f "$FRONTEND_DIR/frontend.pid" ]; then
        FRONTEND_PID=$(cat "$FRONTEND_DIR/frontend.pid")
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            kill "$FRONTEND_PID"
            print_status "Frontend stopped"
        fi
        rm -f "$FRONTEND_DIR/frontend.pid"
    fi
    
    # Fallback cleanup
    pkill -f "app_enhanced" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    
    print_status "All services stopped"
}

# Main execution
main() {
    SERVER_IP=$(get_server_ip)
    
    print_header "🤖 RVTool AI-Enhanced Platform (Fixed Version)"
    print_info "Server IP: $SERVER_IP"
    echo ""
    
    case "${1:-start}" in
        "start")
            stop_existing_services
            
            if start_backend; then
                print_status "Backend startup completed"
            else
                print_error "Backend startup failed"
                exit 1
            fi
            
            if start_frontend; then
                print_status "Frontend startup completed"
            else
                print_error "Frontend startup failed - but continuing..."
            fi
            
            sleep 5
            test_services
            display_service_info
            
            print_info "Services are running. Press Ctrl+C to exit monitoring."
            
            # Simple monitoring loop
            while true; do
                sleep 30
                if ! curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
                    print_error "Backend health check failed!"
                fi
                if ! curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
                    print_error "Frontend not responding!"
                fi
            done
            ;;
        "stop")
            stop_services
            ;;
        "status")
            test_services
            ;;
        "logs")
            show_logs
            ;;
        *)
            echo "Usage: $0 {start|stop|status|logs}"
            exit 1
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}Monitoring stopped. Services are still running.${NC}"; exit 0' INT

# Run main function
main "$@"
