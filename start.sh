#!/bin/bash

# Quantitative Trading Platform - Development Server Startup Script
# This script starts both backend and frontend development servers

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
PID_DIR="$PROJECT_ROOT/.pids"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create PID directory if it doesn't exist
mkdir -p "$PID_DIR"

# Function to log messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a process is running
is_process_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to start backend
start_backend() {
    log_info "Starting backend server..."

    if is_process_running "$PID_DIR/backend.pid"; then
        log_warning "Backend is already running (PID: $(cat $PID_DIR/backend.pid))"
        return 0
    fi

    cd "$BACKEND_DIR"

    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        log_info "Activating Python virtual environment..."
        source venv/bin/activate
    else
        log_warning "Virtual environment not found. Using system Python."
    fi

    # Start backend in background
    # Set PYTHONPATH to project root to enable absolute imports
    PYTHONPATH="$PROJECT_ROOT" python main.py > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
    local backend_pid=$!
    echo $backend_pid > "$PID_DIR/backend.pid"

    # Wait a bit and check if process is still running
    sleep 2
    if ps -p $backend_pid > /dev/null 2>&1; then
        log_success "Backend started successfully (PID: $backend_pid)"
        log_info "Backend running at: ${GREEN}http://localhost:8000${NC}"
        log_info "Backend logs: $PROJECT_ROOT/logs/backend.log"
    else
        log_error "Backend failed to start. Check logs at: $PROJECT_ROOT/logs/backend.log"
        return 1
    fi

    cd "$PROJECT_ROOT"
}

# Function to start frontend
start_frontend() {
    log_info "Starting frontend server..."

    if is_process_running "$PID_DIR/frontend.pid"; then
        log_warning "Frontend is already running (PID: $(cat $PID_DIR/frontend.pid))"
        return 0
    fi

    cd "$FRONTEND_DIR"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        log_info "Installing frontend dependencies..."
        pnpm install
    fi

    # Start frontend in background
    pnpm dev > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
    local frontend_pid=$!
    echo $frontend_pid > "$PID_DIR/frontend.pid"

    # Wait a bit and check if process is still running
    sleep 3
    if ps -p $frontend_pid > /dev/null 2>&1; then
        log_success "Frontend started successfully (PID: $frontend_pid)"
        log_info "Frontend running at: ${GREEN}http://localhost:3002${NC}"
        log_info "Frontend logs: $PROJECT_ROOT/logs/frontend.log"
    else
        log_error "Frontend failed to start. Check logs at: $PROJECT_ROOT/logs/frontend.log"
        return 1
    fi

    cd "$PROJECT_ROOT"
}

# Function to stop all services
stop_services() {
    log_info "Stopping all services..."

    # Stop backend
    if [ -f "$PID_DIR/backend.pid" ]; then
        local backend_pid=$(cat "$PID_DIR/backend.pid")
        if ps -p $backend_pid > /dev/null 2>&1; then
            kill $backend_pid
            log_success "Backend stopped (PID: $backend_pid)"
        fi
        rm -f "$PID_DIR/backend.pid"
    fi

    # Stop frontend
    if [ -f "$PID_DIR/frontend.pid" ]; then
        local frontend_pid=$(cat "$PID_DIR/frontend.pid")
        if ps -p $frontend_pid > /dev/null 2>&1; then
            kill $frontend_pid
            log_success "Frontend stopped (PID: $frontend_pid)"
        fi
        rm -f "$PID_DIR/frontend.pid"
    fi

    log_success "All services stopped"
}

# Function to show status
show_status() {
    echo ""
    log_info "Service Status:"
    echo "================"

    # Backend status
    if is_process_running "$PID_DIR/backend.pid"; then
        echo -e "Backend:  ${GREEN}● Running${NC} (PID: $(cat $PID_DIR/backend.pid)) - http://localhost:8000"
    else
        echo -e "Backend:  ${RED}○ Stopped${NC}"
    fi

    # Frontend status
    if is_process_running "$PID_DIR/frontend.pid"; then
        echo -e "Frontend: ${GREEN}● Running${NC} (PID: $(cat $PID_DIR/frontend.pid)) - http://localhost:3002"
    else
        echo -e "Frontend: ${RED}○ Stopped${NC}"
    fi

    echo ""
}

# Function to show logs
show_logs() {
    local service=$1

    if [ "$service" == "backend" ]; then
        log_info "Backend logs (Ctrl+C to exit):"
        tail -f "$PROJECT_ROOT/logs/backend.log"
    elif [ "$service" == "frontend" ]; then
        log_info "Frontend logs (Ctrl+C to exit):"
        tail -f "$PROJECT_ROOT/logs/frontend.log"
    else
        log_error "Usage: $0 logs [backend|frontend]"
        exit 1
    fi
}

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# Main script logic
case "${1:-start}" in
    start)
        log_info "Starting Quantitative Trading Platform..."
        echo ""
        start_backend
        start_frontend
        echo ""
        show_status
        log_success "All services started successfully!"
        log_info "To stop services, run: ./start.sh stop"
        log_info "To view status, run: ./start.sh status"
        log_info "To view logs, run: ./start.sh logs [backend|frontend]"
        ;;

    stop)
        stop_services
        ;;

    restart)
        stop_services
        echo ""
        sleep 2
        $0 start
        ;;

    status)
        show_status
        ;;

    logs)
        show_logs "$2"
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status|logs [backend|frontend]}"
        echo ""
        echo "Commands:"
        echo "  start   - Start all services (default)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  status  - Show service status"
        echo "  logs    - View logs (backend or frontend)"
        exit 1
        ;;
esac
