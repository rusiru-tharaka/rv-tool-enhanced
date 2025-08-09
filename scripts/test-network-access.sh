#!/bin/bash

# RVTool Enhanced UX - Network Access Test Script
# Tests network accessibility of development servers

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

# Get network IP address
NETWORK_IP=$(hostname -I | awk '{print $1}')

echo "🔍 Testing RVTool Enhanced UX Network Accessibility..."
echo ""

print_info "Network IP Address: $NETWORK_IP"
echo ""

# Test Backend
print_info "Testing Backend API (Port 8000)..."
if curl -s --connect-timeout 5 http://$NETWORK_IP:8000/health > /dev/null; then
    print_status "Backend API is accessible at http://$NETWORK_IP:8000"
    
    # Test specific endpoints
    if curl -s --connect-timeout 5 http://$NETWORK_IP:8000/api/health > /dev/null; then
        print_status "API health endpoint is working"
    else
        print_warning "API health endpoint not responding"
    fi
    
    if curl -s --connect-timeout 5 http://$NETWORK_IP:8000/docs > /dev/null; then
        print_status "API documentation is accessible at http://$NETWORK_IP:8000/docs"
    else
        print_warning "API documentation not accessible"
    fi
else
    print_error "Backend API is not accessible at http://$NETWORK_IP:8000"
fi

echo ""

# Test Frontend
print_info "Testing Frontend (Port 3000)..."
if curl -s --connect-timeout 5 -I http://$NETWORK_IP:3000 | head -1 | grep -q "200 OK"; then
    print_status "Frontend is accessible at http://$NETWORK_IP:3000"
else
    print_error "Frontend is not accessible at http://$NETWORK_IP:3000"
fi

echo ""

# Show listening ports
print_info "Current listening ports:"
ss -tlnp | grep -E ':3000|:8000' | while read line; do
    echo "  $line"
done

echo ""

# Show firewall status (if available)
if command -v ufw >/dev/null 2>&1; then
    print_info "UFW Firewall Status:"
    sudo ufw status 2>/dev/null || echo "  UFW not configured or accessible"
else
    print_info "UFW firewall not installed"
fi

echo ""

print_info "🌐 Network Access URLs:"
echo "  • Frontend: http://$NETWORK_IP:3000"
echo "  • Backend API: http://$NETWORK_IP:8000"
echo "  • API Documentation: http://$NETWORK_IP:8000/docs"

echo ""
print_info "📝 Notes:"
echo "  • Both servers are configured to bind to 0.0.0.0 (all interfaces)"
echo "  • Make sure your network/firewall allows access to ports 3000 and 8000"
echo "  • If accessing from outside the local network, check security groups/firewall rules"
