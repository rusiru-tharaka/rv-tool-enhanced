# Development Scripts Documentation

This document describes the development scripts available for the RVTool Enhanced UX platform.

## 🚀 Available Scripts

### 1. `./scripts/start-dev.sh` - Start Development Servers (Background Mode)

**Purpose**: Starts both backend and frontend development servers in background mode with proper process management.

**Features**:
- ✅ Runs servers in background (non-blocking)
- ✅ Automatic process management with PID files
- ✅ Stops existing servers before starting new ones
- ✅ Comprehensive error handling and logging
- ✅ Health checks for successful startup
- ✅ Automatic setup if dependencies are missing

**Usage**:
```bash
cd /home/ubuntu/rv-tool-enhanced
./scripts/start-dev.sh
```

**Output**:
- Backend server starts on port 8000
- Frontend server starts on port 5173
- Logs are written to `logs/backend_dev.log` and `logs/frontend_dev.log`
- PID files are created for process management

### 2. `./scripts/stop-dev.sh` - Stop Development Servers

**Purpose**: Stops background development servers gracefully.

**Features**:
- ✅ Graceful shutdown with fallback to force kill
- ✅ Cleans up PID files automatically
- ✅ Multiple operation modes
- ✅ Orphaned process cleanup

**Usage**:
```bash
# Stop servers (default)
./scripts/stop-dev.sh

# Show server status
./scripts/stop-dev.sh status

# Clean up orphaned processes
./scripts/stop-dev.sh cleanup

# Force stop all processes
./scripts/stop-dev.sh force
```

### 3. `./scripts/status-dev.sh` - Check Server Status

**Purpose**: Shows detailed status of development servers.

**Features**:
- ✅ Process status and PID information
- ✅ Port availability checking
- ✅ Process uptime information
- ✅ Log file status and recent entries
- ✅ Multiple detail levels

**Usage**:
```bash
# Quick status (default)
./scripts/status-dev.sh

# Detailed status
./scripts/status-dev.sh detailed

# Show recent logs
./scripts/status-dev.sh logs

# Show everything
./scripts/status-dev.sh all
```

### 4. `./scripts/setup.sh` - Environment Setup

**Purpose**: Sets up the development environment with all dependencies.

**Features**:
- ✅ Creates Python virtual environment
- ✅ Installs backend dependencies
- ✅ Installs frontend dependencies
- ✅ Creates environment files if missing

**Usage**:
```bash
./scripts/setup.sh
```

## 📁 File Structure

```
scripts/
├── setup.sh           # Environment setup
├── start-dev.sh        # Start servers (background)
├── stop-dev.sh         # Stop servers
└── status-dev.sh       # Check status

logs/                   # Created automatically
├── backend_dev.log     # Backend server logs
└── frontend_dev.log    # Frontend server logs

backend/
└── backend_dev.pid     # Backend process ID

frontend/
└── frontend_dev.pid    # Frontend process ID
```

## 🔄 Typical Development Workflow

### Initial Setup
```bash
cd /home/ubuntu/rv-tool-enhanced
./scripts/setup.sh
```

### Start Development
```bash
./scripts/start-dev.sh
```

### Check Status
```bash
./scripts/status-dev.sh
```

### View Logs (in separate terminals)
```bash
# Backend logs
tail -f logs/backend_dev.log

# Frontend logs
tail -f logs/frontend_dev.log
```

### Stop Development
```bash
./scripts/stop-dev.sh
```

## 🌐 Access Points

When servers are running:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🔧 Process Management

### PID Files
- Backend: `backend/backend_dev.pid`
- Frontend: `frontend/frontend_dev.pid`

### Log Files
- Backend: `logs/backend_dev.log`
- Frontend: `logs/frontend_dev.log`

### Manual Process Management
```bash
# Check if processes are running
ps -p $(cat backend/backend_dev.pid) 2>/dev/null && echo "Backend running"
ps -p $(cat frontend/frontend_dev.pid) 2>/dev/null && echo "Frontend running"

# Manual stop
kill $(cat backend/backend_dev.pid) 2>/dev/null
kill $(cat frontend/frontend_dev.pid) 2>/dev/null

# Check port usage
lsof -i :8000  # Backend port
lsof -i :5173  # Frontend port
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Check what's using the port
lsof -i :8000
lsof -i :5173

# Kill processes using the ports
./scripts/stop-dev.sh cleanup
```

#### 2. Stale PID Files
```bash
# Clean up stale PID files
rm -f backend/backend_dev.pid frontend/frontend_dev.pid
```

#### 3. Permission Issues
```bash
# Make scripts executable
chmod +x scripts/*.sh
```

#### 4. Dependencies Missing
```bash
# Re-run setup
./scripts/setup.sh
```

### Log Analysis
```bash
# Check for errors in backend logs
grep -i error logs/backend_dev.log

# Check for errors in frontend logs
grep -i error logs/frontend_dev.log

# Follow logs in real-time
tail -f logs/backend_dev.log logs/frontend_dev.log
```

## 🔄 Script Updates

The scripts are designed to be:
- **Self-healing**: Automatically handle common issues
- **Idempotent**: Safe to run multiple times
- **Robust**: Handle edge cases and errors gracefully
- **Informative**: Provide clear status and error messages

## 📝 Notes

1. **Background Mode**: Servers run in background, allowing you to continue using the terminal
2. **Process Safety**: Scripts check for existing processes and handle them appropriately
3. **Log Management**: All output is logged to files for debugging
4. **Health Checks**: Scripts verify that servers started successfully
5. **Cleanup**: Automatic cleanup of PID files and orphaned processes

---

**Last Updated**: August 5, 2025  
**Version**: 2.0.0
