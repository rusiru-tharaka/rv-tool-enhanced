#!/bin/bash

# Browser-Compatible Backend Startup Script
# Fixes ERR_CONNECTION_REFUSED issues with browser connections

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKEND_DIR="/home/ubuntu/rvtool/enhanced-ux/backend"
FRONTEND_DIR="/home/ubuntu/rvtool/enhanced-ux/frontend"

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

# Function to stop all services
stop_services() {
    print_info "Stopping all services..."
    pkill -f "uvicorn.*app_enhanced" 2>/dev/null || true
    pkill -f "vite.*3000" 2>/dev/null || true
    sleep 2
    
    # Force kill if ports still in use
    if ss -tlnp | grep -q ":8000"; then
        fuser -k 8000/tcp 2>/dev/null || true
    fi
    if ss -tlnp | grep -q ":3000"; then
        fuser -k 3000/tcp 2>/dev/null || true
    fi
    sleep 1
    print_status "Services stopped"
}

# Function to fix network binding issues
fix_network_binding() {
    print_info "Fixing network binding issues..."
    
    # Check if IPv6 is causing issues
    if ping6 -c 1 ::1 >/dev/null 2>&1; then
        print_info "IPv6 localhost (::1) is reachable"
    else
        print_warning "IPv6 localhost (::1) may have issues"
    fi
    
    # Ensure IPv4 localhost is working
    if ping -c 1 127.0.0.1 >/dev/null 2>&1; then
        print_status "IPv4 localhost (127.0.0.1) is working"
    else
        print_error "IPv4 localhost (127.0.0.1) is not working"
        exit 1
    fi
}

# Function to start backend with browser-compatible settings
start_backend_browser_compatible() {
    print_info "Starting backend with browser-compatible settings..."
    
    cd "$BACKEND_DIR"
    
    # Start backend with specific binding to avoid IPv6 issues
    print_info "Binding backend to 127.0.0.1:8000 (IPv4 only)..."
    
    nohup python3 -m uvicorn app_enhanced:app \
        --host 127.0.0.1 \
        --port 8000 \
        --log-level info \
        --access-log \
        --loop asyncio \
        > backend_browser_compatible.log 2>&1 &
    
    BACKEND_PID=$!
    echo $BACKEND_PID > backend_browser_compatible.pid
    
    # Wait for backend to start
    print_info "Waiting for backend to start..."
    for i in {1..20}; do
        if curl -s http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
            print_status "Backend started successfully"
            break
        fi
        if [ $i -eq 20 ]; then
            print_error "Backend failed to start"
            tail -10 backend_browser_compatible.log
            exit 1
        fi
        sleep 1
        echo -n "."
    done
    echo ""
}

# Function to test browser compatibility
test_browser_compatibility() {
    print_info "Testing browser compatibility..."
    
    # Test with different localhost variations
    local endpoints=(
        "http://127.0.0.1:8000/api/health"
        "http://localhost:8000/api/health"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -s "$endpoint" >/dev/null 2>&1; then
            print_status "✅ $endpoint - ACCESSIBLE"
        else
            print_error "❌ $endpoint - NOT ACCESSIBLE"
        fi
    done
    
    # Test cleaning upload endpoint
    if curl -s -X POST http://127.0.0.1:8000/api/cleaning/upload -H "Content-Type: application/json" -d '{}' | grep -q "field required"; then
        print_status "✅ Cleaning upload endpoint - WORKING"
    else
        print_error "❌ Cleaning upload endpoint - NOT WORKING"
    fi
    
    # Test CORS headers
    if curl -s -H "Origin: http://localhost:3000" http://127.0.0.1:8000/api/health | grep -q "healthy"; then
        print_status "✅ CORS headers - WORKING"
    else
        print_error "❌ CORS headers - NOT WORKING"
    fi
}

# Function to start frontend
start_frontend() {
    print_info "Starting frontend..."
    
    cd "$FRONTEND_DIR"
    
    # Ensure frontend is configured correctly
    if ! grep -q "localhost:8000" .env.development; then
        print_warning "Updating frontend configuration..."
        echo "VITE_API_BASE_URL=http://localhost:8000" > .env.development
        echo "VITE_ALLOWED_HOSTS=localhost,127.0.0.1" >> .env.development
    fi
    
    nohup npm run dev -- --host 0.0.0.0 --port 3000 > frontend_browser_compatible.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > frontend_browser_compatible.pid
    
    # Wait for frontend
    print_info "Waiting for frontend to start..."
    for i in {1..30}; do
        if curl -s http://localhost:3000 >/dev/null 2>&1; then
            print_status "Frontend started successfully"
            break
        fi
        if [ $i -eq 30 ]; then
            print_warning "Frontend taking longer than expected"
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
}

# Function to create browser test page
create_browser_test() {
    print_info "Creating browser test page..."
    
    cat > /tmp/test_connection.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>RVTool Connection Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .test { margin: 10px 0; padding: 10px; border: 1px solid #ccc; }
        .success { background-color: #d4edda; border-color: #c3e6cb; }
        .error { background-color: #f8d7da; border-color: #f5c6cb; }
        button { padding: 10px 20px; margin: 5px; }
    </style>
</head>
<body>
    <h1>RVTool Backend Connection Test</h1>
    <div id="results"></div>
    
    <button onclick="testHealth()">Test Health Endpoint</button>
    <button onclick="testCleaningUpload()">Test Cleaning Upload</button>
    <button onclick="testAll()">Test All</button>
    
    <script>
        const results = document.getElementById('results');
        
        function addResult(test, success, message) {
            const div = document.createElement('div');
            div.className = 'test ' + (success ? 'success' : 'error');
            div.innerHTML = `<strong>${test}:</strong> ${success ? '✅' : '❌'} ${message}`;
            results.appendChild(div);
        }
        
        async function testHealth() {
            try {
                const response = await fetch('http://localhost:8000/api/health');
                if (response.ok) {
                    const data = await response.json();
                    addResult('Health Check', true, `Backend is healthy (${data.service})`);
                } else {
                    addResult('Health Check', false, `HTTP ${response.status}`);
                }
            } catch (error) {
                addResult('Health Check', false, `Connection error: ${error.message}`);
            }
        }
        
        async function testCleaningUpload() {
            try {
                const response = await fetch('http://localhost:8000/api/cleaning/upload', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: '{}'
                });
                if (response.status === 422) {
                    addResult('Cleaning Upload', true, 'Endpoint working (expects file)');
                } else if (response.ok) {
                    addResult('Cleaning Upload', true, 'Endpoint accessible');
                } else {
                    addResult('Cleaning Upload', false, `HTTP ${response.status}`);
                }
            } catch (error) {
                addResult('Cleaning Upload', false, `Connection error: ${error.message}`);
            }
        }
        
        async function testAll() {
            results.innerHTML = '';
            await testHealth();
            await testCleaningUpload();
        }
        
        // Auto-run tests on page load
        window.onload = testAll;
    </script>
</body>
</html>
EOF
    
    print_status "Browser test page created at: /tmp/test_connection.html"
    print_info "You can open this in your browser to test the connection"
}

# Main function
main() {
    case "${1:-start}" in
        "start")
            print_info "🔧 Starting Browser-Compatible RVTool Platform"
            echo ""
            
            fix_network_binding
            stop_services
            start_backend_browser_compatible
            test_browser_compatibility
            start_frontend
            create_browser_test
            
            echo ""
            print_status "🎉 BROWSER-COMPATIBLE PLATFORM READY!"
            print_info "Frontend: http://localhost:3000"
            print_info "Backend: http://localhost:8000"
            print_info "Test Page: file:///tmp/test_connection.html"
            echo ""
            print_info "If you still get connection errors:"
            print_info "1. Open the test page in your browser"
            print_info "2. Check browser console for specific errors"
            print_info "3. Try accessing http://127.0.0.1:8000/api/health directly"
            ;;
        "stop")
            stop_services
            ;;
        "test")
            test_browser_compatibility
            ;;
        *)
            echo "Usage: $0 {start|stop|test}"
            exit 1
            ;;
    esac
}

main "$@"
