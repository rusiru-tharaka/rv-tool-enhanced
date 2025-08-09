#!/bin/bash

# RVTool Enhanced UX - Development Start Script (Background Mode)
# Starts both backend and frontend in development mode as background processes

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
LOG_DIR="logs"

# Create logs directory
mkdir -p $LOG_DIR

echo "🚀 Starting RVTool Enhanced UX Development Environment (Background Mode)..."

# Function to check if a process is running
is_process_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # Process is running
        else
            rm -f "$pid_file"  # Clean up stale PID file
            return 1  # Process is not running
        fi
    fi
    return 1  # PID file doesn't exist
}

# Function to stop existing processes
stop_existing_processes() {
    print_info "Checking for existing development servers..."
    
    if is_process_running "$BACKEND_PID_FILE"; then
        local backend_pid=$(cat "$BACKEND_PID_FILE")
        print_info "Stopping existing backend server (PID: $backend_pid)..."
        kill "$backend_pid" 2>/dev/null || true
        rm -f "$BACKEND_PID_FILE"
    fi
    
    if is_process_running "$FRONTEND_PID_FILE"; then
        local frontend_pid=$(cat "$FRONTEND_PID_FILE")
        print_info "Stopping existing frontend server (PID: $frontend_pid)..."
        kill "$frontend_pid" 2>/dev/null || true
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    # Wait a moment for processes to stop
    sleep 2
}

# Function to start backend
start_backend() {
    print_info "Starting backend server in background..."
    cd backend
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_warning "Backend virtual environment not found. Running setup..."
        cd ..
        ./scripts/setup.sh
        cd backend
    fi
    
    # Start backend server with simple API implementation for development
    source venv/bin/activate
    nohup uvicorn app.simple_main:app --reload --host 0.0.0.0 --port 8000 > "../$LOG_DIR/backend_dev.log" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "../$BACKEND_PID_FILE"
    cd ..
    
    # Wait and check if backend started successfully
    sleep 3
    if is_process_running "$BACKEND_PID_FILE"; then
        print_status "Backend server started successfully (PID: $BACKEND_PID)"
    else
        print_error "Failed to start backend server"
        return 1
    fi
}

# Function to start frontend
start_frontend() {
    print_info "Starting frontend development server in background..."
    cd frontend
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        print_warning "Frontend dependencies not found. Running setup..."
        cd ..
        ./scripts/setup.sh
        cd frontend
    fi
    
    # Start frontend server in local mode
    nohup npm run dev:local > "../$LOG_DIR/frontend_dev.log" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "../$FRONTEND_PID_FILE"
    cd ..
    
    # Wait and check if frontend started successfully
    sleep 5
    if is_process_running "$FRONTEND_PID_FILE"; then
        print_status "Frontend server started successfully (PID: $FRONTEND_PID)"
    else
        print_error "Failed to start frontend server"
        return 1
    fi
}

# Function to show status
show_status() {
    # Get network IP address
    NETWORK_IP=$(hostname -I | awk '{print $1}')
    
    echo ""
    print_status "🎉 Development environment started successfully!"
    echo ""
    print_info "📍 Local Access Points:"
    echo "  • Frontend: http://localhost:3000"
    echo "  • Backend API: http://localhost:8000"
    echo "  • API Documentation: http://localhost:8000/docs"
    echo ""
    print_info "🌐 Network Access Points:"
    echo "  • Frontend: http://$NETWORK_IP:3000"
    echo "  • Backend API: http://$NETWORK_IP:8000"
    echo "  • API Documentation: http://$NETWORK_IP:8000/docs"
    echo ""
    print_info "📋 Process Information:"
    if is_process_running "$BACKEND_PID_FILE"; then
        echo "  • Backend PID: $(cat $BACKEND_PID_FILE)"
    fi
    if is_process_running "$FRONTEND_PID_FILE"; then
        echo "  • Frontend PID: $(cat $FRONTEND_PID_FILE)"
    fi
    echo ""
    print_info "📄 Log Files:"
    echo "  • Backend logs: $LOG_DIR/backend_dev.log"
    echo "  • Frontend logs: $LOG_DIR/frontend_dev.log"
    echo ""
    print_info "🛑 To stop servers:"
    echo "  • Run: ./scripts/stop-dev.sh"
    echo "  • Or manually: kill \$(cat $BACKEND_PID_FILE) \$(cat $FRONTEND_PID_FILE)"
    echo ""
    print_info "🔧 Network Configuration:"
    echo "  • Backend binds to: 0.0.0.0:8000 (accessible from network)"
    echo "  • Frontend binds to: 0.0.0.0:3000 (accessible from network)"
    echo "  • Current network IP: $NETWORK_IP"
}

# Main execution
main() {
    # Stop any existing processes
    stop_existing_processes
    
    # Start backend
    if ! start_backend; then
        print_error "Failed to start backend. Check logs: $LOG_DIR/backend_dev.log"
        exit 1
    fi
    
    # Start frontend
    if ! start_frontend; then
        print_error "Failed to start frontend. Check logs: $LOG_DIR/frontend_dev.log"
        # Stop backend if frontend fails
        if is_process_running "$BACKEND_PID_FILE"; then
            kill "$(cat $BACKEND_PID_FILE)" 2>/dev/null || true
            rm -f "$BACKEND_PID_FILE"
        fi
        exit 1
    fi
    
    # Show status
    show_status
}

# Run main function
main
