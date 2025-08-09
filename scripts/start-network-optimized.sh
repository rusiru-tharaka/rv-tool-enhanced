#!/bin/bash

# RVTool Platform Startup Script - NETWORK OPTIMIZED
# Ensures backend binds to network interface for reliable connections
# Version: 2.2 - Network Binding Fix

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

# Get network IP
get_network_ip() {
    NETWORK_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7}' | head -1)
    
    if [ -z "$NETWORK_IP" ]; then
        NETWORK_IP=$(hostname -I | awk '{print $1}')
    fi
    
    if [ -z "$NETWORK_IP" ]; then
        NETWORK_IP="10.0.7.44"  # Fallback to known IP
    fi
    
    echo "$NETWORK_IP"
}

NETWORK_IP=$(get_network_ip)

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

# Function to test network connectivity
test_network_connectivity() {
    print_info "Testing network connectivity..."
    
    # Test if we can bind to the network interface
    if python3 -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('$NETWORK_IP', 0))
    s.close()
    print('✅ Can bind to network interface $NETWORK_IP')
except Exception as e:
    print(f'❌ Cannot bind to network interface $NETWORK_IP: {e}')
    exit(1)
"; then
        print_status "Network interface $NETWORK_IP is available"
    else
        print_error "Cannot bind to network interface $NETWORK_IP"
        exit 1
    fi
    
    # Test if port 8000 is available
    if ! ss -tlnp | grep -q ":$BACKEND_PORT"; then
        print_status "Port $BACKEND_PORT is available"
    else
        print_error "Port $BACKEND_PORT is already in use"
        exit 1
    fi
}

# Function to start backend with network binding
start_backend_network() {
    print_header "🚀 Starting Backend with Network Binding"
    
    cd "$BACKEND_DIR"
    
    print_fix "Starting backend bound to network interface: $NETWORK_IP:$BACKEND_PORT"
    print_info "Backend will be accessible on:"
    print_info "  • Network: http://$NETWORK_IP:$BACKEND_PORT"
    print_info "  • Localhost: http://localhost:$BACKEND_PORT"
    print_info "  • All interfaces: http://0.0.0.0:$BACKEND_PORT"
    
    # Start backend bound to all interfaces (0.0.0.0) for maximum compatibility
    # This allows access from localhost, network IP, and external connections
    nohup python3 -m uvicorn app_enhanced:app \
        --host 0.0.0.0 \
        --port $BACKEND_PORT \
        --log-level info \
        --access-log \
        --workers 1 \
        > backend_network.log 2>&1 &
    
    BACKEND_PID=$!
    echo $BACKEND_PID > backend_network.pid
    
    # Wait for backend to start
    print_info "Waiting for backend to initialize on network interface..."
    for i in {1..30}; do
        # Test both network IP and localhost
        if curl -s http://$NETWORK_IP:$BACKEND_PORT/api/health > /dev/null 2>&1 || \
           curl -s http://localhost:$BACKEND_PORT/api/health > /dev/null 2>&1; then
            print_status "Backend started successfully on network interface"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Backend failed to start within 30 seconds"
            print_info "Check backend_network.log for errors:"
            tail -20 backend_network.log
            exit 1
        fi
        sleep 1
        if [ $((i % 5)) -eq 0 ]; then
            echo -n " [$i/30]"
        else
            echo -n "."
        fi
    done
    echo ""
    
    # Test all access methods
    print_info "Testing backend accessibility..."
    
    # Test network IP access
    if curl -s http://$NETWORK_IP:$BACKEND_PORT/api/health | grep -q "healthy"; then
        print_status "✅ Network IP access: http://$NETWORK_IP:$BACKEND_PORT"
    else
        print_warning "⚠️  Network IP access may have issues"
    fi
    
    # Test localhost access
    if curl -s http://localhost:$BACKEND_PORT/api/health | grep -q "healthy"; then
        print_status "✅ Localhost access: http://localhost:$BACKEND_PORT"
    else
        print_warning "⚠️  Localhost access may have issues"
    fi
    
    # Test cleaning endpoints
    if curl -s http://$NETWORK_IP:$BACKEND_PORT/api/cleaning/health > /dev/null 2>&1; then
        print_status "✅ Cleaning endpoints accessible"
    else
        print_warning "⚠️  Cleaning endpoints may not be accessible"
    fi
}

# Function to start frontend with network configuration
start_frontend_network() {
    print_header "🌐 Starting Frontend with Network Configuration"
    
    cd "$FRONTEND_DIR"
    
    # Ensure frontend is configured for network IP
    print_info "Configuring frontend for network access..."
    
    if grep -q "$NETWORK_IP:8000" .env.development; then
        print_status "Frontend already configured for network IP"
    else
        print_fix "Updating frontend configuration for network IP..."
        cat > .env.development << EOF
# Development Environment Configuration - Network IP (Connection Fix)
VITE_API_BASE_URL=http://$NETWORK_IP:8000
VITE_ALLOWED_HOSTS=localhost,127.0.0.1,$NETWORK_IP,rvtool-alb-dev-1648331028.us-east-1.elb.amazonaws.com
VITE_APP_TITLE=RVTool Migration Analysis Platform (Dev-Network)
VITE_APP_VERSION=2.0.0-dev-network
EOF
        print_status "Frontend configuration updated"
    fi
    
    print_fix "Starting frontend with network binding..."
    print_info "Frontend will be accessible on:"
    print_info "  • Network: http://$NETWORK_IP:$FRONTEND_PORT"
    print_info "  • Localhost: http://localhost:$FRONTEND_PORT"
    
    # Start frontend bound to all interfaces
    nohup npm run dev -- --host 0.0.0.0 --port $FRONTEND_PORT > frontend_network.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > frontend_network.pid
    
    # Wait for frontend to start
    print_info "Waiting for frontend to build and start..."
    for i in {1..45}; do
        if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1 || \
           curl -s http://$NETWORK_IP:$FRONTEND_PORT > /dev/null 2>&1; then
            print_status "Frontend started successfully"
            break
        fi
        if [ $i -eq 45 ]; then
            print_warning "Frontend taking longer than expected to start"
            break
        fi
        sleep 1
        if [ $((i % 10)) -eq 0 ]; then
            echo -n " [$i/45]"
        else
            echo -n "."
        fi
    done
    echo ""
}

# Function to test end-to-end connectivity
test_e2e_connectivity() {
    print_header "🧪 Testing End-to-End Connectivity"
    
    print_info "Testing backend endpoints from different access methods..."
    
    # Test network IP access
    print_info "Testing network IP access ($NETWORK_IP:8000)..."
    if curl -s -X POST http://$NETWORK_IP:8000/api/cleaning/upload \
        -H "Origin: http://$NETWORK_IP:3000" \
        -H "Content-Type: application/json" \
        -d '{}' | grep -q "field required"; then
        print_status "✅ Network IP cleaning upload: WORKING"
    else
        print_error "❌ Network IP cleaning upload: FAILED"
    fi
    
    # Test localhost access
    print_info "Testing localhost access (localhost:8000)..."
    if curl -s -X POST http://localhost:8000/api/cleaning/upload \
        -H "Origin: http://localhost:3000" \
        -H "Content-Type: application/json" \
        -d '{}' | grep -q "field required"; then
        print_status "✅ Localhost cleaning upload: WORKING"
    else
        print_warning "⚠️  Localhost cleaning upload: May have issues"
    fi
    
    # Test CORS headers
    print_info "Testing CORS configuration..."
    CORS_ORIGIN=$(curl -s -H "Origin: http://$NETWORK_IP:3000" \
        http://$NETWORK_IP:8000/api/health | \
        grep -o '"Access-Control-Allow-Origin":"[^"]*"' || echo "")
    
    if [ -n "$CORS_ORIGIN" ]; then
        print_status "✅ CORS headers: CONFIGURED"
    else
        print_warning "⚠️  CORS headers: May need attention"
    fi
}

# Function to display service information
display_service_info() {
    print_header "🎉 NETWORK-OPTIMIZED PLATFORM STARTED!"
    
    echo ""
    print_fix "🌐 NETWORK ACCESS INFORMATION:"
    echo ""
    print_status "Network IP: $NETWORK_IP"
    print_status "Backend Network Access: http://$NETWORK_IP:$BACKEND_PORT"
    print_status "Frontend Network Access: http://$NETWORK_IP:$FRONTEND_PORT"
    echo ""
    print_status "Backend Localhost Access: http://localhost:$BACKEND_PORT"
    print_status "Frontend Localhost Access: http://localhost:$FRONTEND_PORT"
    echo ""
    
    print_info "🎯 RECOMMENDED ACCESS METHODS:"
    echo ""
    print_status "Primary: http://$NETWORK_IP:$FRONTEND_PORT"
    print_status "Alternative: http://localhost:$FRONTEND_PORT"
    echo ""
    
    print_info "🔧 API ENDPOINTS:"
    echo ""
    print_status "Health Check: http://$NETWORK_IP:$BACKEND_PORT/api/health"
    print_status "Cleaning Upload: http://$NETWORK_IP:$BACKEND_PORT/api/cleaning/upload"
    print_status "API Documentation: http://$NETWORK_IP:$BACKEND_PORT/api/docs"
    echo ""
    
    print_info "📋 LOG FILES:"
    echo "  • Backend: $BACKEND_DIR/backend_network.log"
    echo "  • Frontend: $FRONTEND_DIR/frontend_network.log"
    echo ""
    
    print_info "🔧 PROCESS MANAGEMENT:"
    echo "  • Backend PID: $(cat $BACKEND_DIR/backend_network.pid 2>/dev/null || echo 'Not found')"
    echo "  • Frontend PID: $(cat $FRONTEND_DIR/frontend_network.pid 2>/dev/null || echo 'Not found')"
    echo ""
    echo "  TO STOP: $0 stop"
    echo ""
    
    print_status "🚀 STATUS: NETWORK-OPTIMIZED PLATFORM READY!"
    print_fix "Backend is bound to all network interfaces (0.0.0.0:8000)"
    print_fix "Frontend is configured to use network IP ($NETWORK_IP:8000)"
}

# Main execution
main() {
    case "${1:-start}" in
        "start")
            print_header "🔧 RVTool Platform - NETWORK OPTIMIZED"
            echo ""
            print_info "Network IP detected: $NETWORK_IP"
            echo ""
            
            test_network_connectivity
            stop_existing_services
            start_backend_network
            start_frontend_network
            test_e2e_connectivity
            display_service_info
            ;;
        "stop")
            print_info "Stopping network-optimized platform..."
            stop_existing_services
            print_status "Platform stopped"
            ;;
        "status")
            print_info "Checking platform status..."
            if ss -tlnp | grep -q ":$BACKEND_PORT"; then
                print_status "Backend running on port $BACKEND_PORT"
                if curl -s http://$NETWORK_IP:$BACKEND_PORT/api/health > /dev/null 2>&1; then
                    print_status "Backend accessible via network IP"
                fi
            else
                print_warning "Backend not running"
            fi
            
            if ss -tlnp | grep -q ":$FRONTEND_PORT"; then
                print_status "Frontend running on port $FRONTEND_PORT"
            else
                print_warning "Frontend not running"
            fi
            ;;
        "test")
            test_e2e_connectivity
            ;;
        *)
            echo "Usage: $0 {start|stop|status|test}"
            echo ""
            echo "  start  - Start platform with network optimization"
            echo "  stop   - Stop all platform services"
            echo "  status - Check service status"
            echo "  test   - Test connectivity"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
