#!/bin/bash

# RVTool Enhanced UX - Development Stop Script
# Stops background development servers

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

echo "🛑 Stopping RVTool Enhanced UX Development Environment..."

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

# Function to stop a process
stop_process() {
    local pid_file=$1
    local service_name=$2
    
    if is_process_running "$pid_file"; then
        local pid=$(cat "$pid_file")
        print_info "Stopping $service_name server (PID: $pid)..."
        
        # Try graceful shutdown first
        kill "$pid" 2>/dev/null || true
        
        # Wait for process to stop
        local count=0
        while [ $count -lt 10 ] && ps -p "$pid" > /dev/null 2>&1; do
            sleep 1
            count=$((count + 1))
        done
        
        # Force kill if still running
        if ps -p "$pid" > /dev/null 2>&1; then
            print_warning "Force killing $service_name server..."
            kill -9 "$pid" 2>/dev/null || true
        fi
        
        # Clean up PID file
        rm -f "$pid_file"
        print_status "$service_name server stopped successfully"
    else
        print_info "$service_name server is not running"
    fi
}

# Function to stop all processes
stop_all_processes() {
    local stopped_any=false
    
    # Stop backend
    if [ -f "$BACKEND_PID_FILE" ]; then
        stop_process "$BACKEND_PID_FILE" "Backend"
        stopped_any=true
    fi
    
    # Stop frontend
    if [ -f "$FRONTEND_PID_FILE" ]; then
        stop_process "$FRONTEND_PID_FILE" "Frontend"
        stopped_any=true
    fi
    
    if [ "$stopped_any" = true ]; then
        echo ""
        print_status "🎉 All development servers stopped successfully!"
    else
        print_info "No development servers were running"
    fi
}

# Function to show status
show_status() {
    echo ""
    print_info "📋 Development Server Status:"
    
    if is_process_running "$BACKEND_PID_FILE"; then
        echo "  • Backend: ✅ Running (PID: $(cat $BACKEND_PID_FILE))"
    else
        echo "  • Backend: ❌ Not running"
    fi
    
    if is_process_running "$FRONTEND_PID_FILE"; then
        echo "  • Frontend: ✅ Running (PID: $(cat $FRONTEND_PID_FILE))"
    else
        echo "  • Frontend: ❌ Not running"
    fi
    echo ""
}

# Function to clean up orphaned processes
cleanup_orphaned() {
    print_info "Cleaning up any orphaned development processes..."
    
    # Kill any uvicorn processes on port 8000
    local uvicorn_pids=$(lsof -ti:8000 2>/dev/null || true)
    if [ ! -z "$uvicorn_pids" ]; then
        print_info "Found uvicorn processes on port 8000, stopping them..."
        echo "$uvicorn_pids" | xargs kill 2>/dev/null || true
    fi
    
    # Kill any vite dev server processes
    local vite_pids=$(pgrep -f "vite.*dev" 2>/dev/null || true)
    if [ ! -z "$vite_pids" ]; then
        print_info "Found Vite dev server processes, stopping them..."
        echo "$vite_pids" | xargs kill 2>/dev/null || true
    fi
}

# Main execution
main() {
    case "${1:-stop}" in
        "stop")
            stop_all_processes
            ;;
        "status")
            show_status
            ;;
        "cleanup")
            cleanup_orphaned
            print_status "Cleanup completed"
            ;;
        "force")
            print_warning "Force stopping all development processes..."
            cleanup_orphaned
            stop_all_processes
            ;;
        *)
            echo "Usage: $0 [stop|status|cleanup|force]"
            echo ""
            echo "Commands:"
            echo "  stop     - Stop development servers (default)"
            echo "  status   - Show server status"
            echo "  cleanup  - Clean up orphaned processes"
            echo "  force    - Force stop all processes"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
