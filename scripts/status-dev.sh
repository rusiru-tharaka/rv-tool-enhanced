#!/bin/bash

# RVTool Enhanced UX - Development Status Script
# Shows current status of development servers with network access information

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# PID files for process management
BACKEND_PID_FILE="backend/backend_dev.pid"
FRONTEND_PID_FILE="frontend/frontend_dev.pid"

# Function to check if a process is running
is_process_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # Process is running
        else
            return 1  # Process is not running
        fi
    fi
    return 1  # PID file doesn't exist
}

# Get network IP address
NETWORK_IP=$(hostname -I | awk '{print $1}')

echo "📊 RVTool Enhanced UX Development Environment Status"
echo ""

# Check Backend Status
print_info "Backend Server Status:"
if is_process_running "$BACKEND_PID_FILE"; then
    BACKEND_PID=$(cat "$BACKEND_PID_FILE")
    print_status "Running (PID: $BACKEND_PID)"
    
    # Test connectivity
    if curl -s --connect-timeout 3 http://localhost:8000/health > /dev/null; then
        print_status "API responding on localhost:8000"
    else
        print_warning "API not responding on localhost:8000"
    fi
    
    if curl -s --connect-timeout 3 http://$NETWORK_IP:8000/health > /dev/null; then
        print_status "API accessible from network: http://$NETWORK_IP:8000"
    else
        print_warning "API not accessible from network"
    fi
else
    print_error "Not running"
fi

echo ""

# Check Frontend Status
print_info "Frontend Server Status:"
if is_process_running "$FRONTEND_PID_FILE"; then
    FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
    print_status "Running (PID: $FRONTEND_PID)"
    
    # Test connectivity
    if curl -s --connect-timeout 3 -I http://localhost:3000 | head -1 | grep -q "200 OK"; then
        print_status "Frontend responding on localhost:3000"
    else
        print_warning "Frontend not responding on localhost:3000"
    fi
    
    if curl -s --connect-timeout 3 -I http://$NETWORK_IP:3000 | head -1 | grep -q "200 OK"; then
        print_status "Frontend accessible from network: http://$NETWORK_IP:3000"
    else
        print_warning "Frontend not accessible from network"
    fi
else
    print_error "Not running"
fi

echo ""

# Show access points if both are running
if is_process_running "$BACKEND_PID_FILE" && is_process_running "$FRONTEND_PID_FILE"; then
    print_info "🌐 Access Points:"
    echo ""
    echo "  📍 Local Access:"
    echo "    • Frontend: http://localhost:3000"
    echo "    • Backend API: http://localhost:8000"
    echo "    • API Docs: http://localhost:8000/docs"
    echo ""
    echo "  🌐 Network Access:"
    echo "    • Frontend: http://$NETWORK_IP:3000"
    echo "    • Backend API: http://$NETWORK_IP:8000"
    echo "    • API Docs: http://$NETWORK_IP:8000/docs"
    echo ""
fi

# Show listening ports
print_info "Listening Ports:"
PORTS=$(ss -tlnp | grep -E ':3000|:8000' | wc -l)
if [ "$PORTS" -gt 0 ]; then
    ss -tlnp | grep -E ':3000|:8000' | while read line; do
        echo "  $line"
    done
else
    echo "  No development servers listening on ports 3000 or 8000"
fi

echo ""

# Show log files
print_info "Log Files:"
if [ -f "logs/backend_dev.log" ]; then
    BACKEND_LOG_SIZE=$(wc -l < logs/backend_dev.log)
    echo "  • Backend: logs/backend_dev.log ($BACKEND_LOG_SIZE lines)"
else
    echo "  • Backend: logs/backend_dev.log (not found)"
fi

if [ -f "logs/frontend_dev.log" ]; then
    FRONTEND_LOG_SIZE=$(wc -l < logs/frontend_dev.log)
    echo "  • Frontend: logs/frontend_dev.log ($FRONTEND_LOG_SIZE lines)"
else
    echo "  • Frontend: logs/frontend_dev.log (not found)"
fi

echo ""

# Show control commands
print_info "Control Commands:"
echo "  • Start: ./scripts/start-dev.sh"
echo "  • Stop: ./scripts/stop-dev.sh"
echo "  • Test Network: ./scripts/test-network-access.sh"
