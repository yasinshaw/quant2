#!/bin/bash
#
# Optuna Storage Server Startup Script
#
# Starts Optuna storage server for distributed optimization.
# Multiple workers can connect to this server to parallelize trials.
#
# Usage:
#   ./scripts/optuna_storage_server.sh [start|stop|status]
#
# Storage options:
#   - SQLite (default): Good for single machine, simple setup
#   - PostgreSQL: Recommended for production
#   - Redis: Fastest, for high-performance scenarios
#

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
STORAGE_TYPE="${OPTUNA_STORAGE_TYPE:-sqlite}"  # sqlite, postgresql, redis
STORAGE_HOST="${OPTUNA_STORAGE_HOST:-localhost}"
STORAGE_PORT="${OPTUNA_STORAGE_PORT:-}"
DB_NAME="${OPTUNA_DB_NAME:-optuna Studies}"
STORAGE_DIR="${PROJECT_ROOT}/data/optuna"
PID_FILE="${STORAGE_DIR}/storage.pid"
LOG_FILE="${STORAGE_DIR}/storage.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create storage directory
mkdir -p "$STORAGE_DIR"

# Storage URLs
case $STORAGE_TYPE in
    sqlite)
        STORAGE_URL="sqlite:///${STORAGE_DIR}/optuna.db"
        ;;
    postgresql)
        STORAGE_URL="postgresql://${OPTUNA_DB_USER:-optuna}:${OPTUNA_DB_PASSWORD:-optuna}@${STORAGE_HOST}:${OPTUNA_DB_PORT:-5432}/${DB_NAME}"
        ;;
    redis)
        STORAGE_URL="redis://${STORAGE_HOST}:${STORAGE_PORT:-6379}"
        ;;
    *)
        echo -e "${RED}Unknown storage type: $STORAGE_TYPE${NC}"
        echo "Supported types: sqlite, postgresql, redis"
        exit 1
        ;;
esac

echo "Storage Type: $STORAGE_TYPE"
echo "Storage URL: $STORAGE_URL"

# Function to check if storage server is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Function to start storage server
start_server() {
    if is_running; then
        echo -e "${YELLOW}Storage server is already running (PID: $(cat $PID_FILE))${NC}"
        return 0
    fi

    echo -e "${GREEN}Starting Optuna storage server...${NC}"
    echo "Storage URL: $STORAGE_URL"
    echo "Log file: $LOG_FILE"

    case $STORAGE_TYPE in
        sqlite)
            # For SQLite, no server needed - just ensure directory exists
            echo -e "${GREEN}SQLite storage ready at: ${STORAGE_DIR}/optuna.db${NC}"
            # Don't create PID file for SQLite (no server process)
            return 0
            ;;
        postgresql)
            # PostgreSQL server should already be running
            # Just verify connection
            if command -v psql &> /dev/null; then
                echo "Verifying PostgreSQL connection..."
                psql "$STORAGE_URL" -c "SELECT 1;" > /dev/null 2>&1 || {
                    echo -e "${RED}Failed to connect to PostgreSQL${NC}"
                    exit 1
                }
            fi
            ;;
        redis)
            # Start Redis server if not running
            if ! pgrep -x "redis-server" > /dev/null; then
                echo "Starting Redis server..."
                redis-server --daemonize yes --port "${STORAGE_PORT:-6379}"
            fi
            ;;
    esac

    # Create PID file
    echo $$ > "$PID_FILE"
    echo -e "${GREEN}Storage server started successfully${NC}"
    echo "Storage URL: $STORAGE_URL"
}

# Function to stop storage server
stop_server() {
    if ! is_running; then
        echo -e "${YELLOW}Storage server is not running${NC}"
        return 0
    fi

    echo -e "${GREEN}Stopping Optuna storage server...${NC}"

    case $STORAGE_TYPE in
        sqlite)
            rm -f "$PID_FILE"
            echo -e "${GREEN}SQLite storage stopped (no server process)${NC}"
            ;;
        redis)
            if pgrep -x "redis-server" > /dev/null; then
                pkill redis-server
            fi
            rm -f "$PID_FILE"
            echo -e "${GREEN}Redis server stopped${NC}"
            ;;
        postgresql)
            # PostgreSQL is a system service, don't stop it
            rm -f "$PID_FILE"
            echo -e "${GREEN}Disconnected from PostgreSQL${NC}"
            ;;
    esac
}

# Function to show status
show_status() {
    echo "Optuna Storage Status:"
    echo "====================="
    echo "Storage Type: $STORAGE_TYPE"
    echo "Storage URL: $STORAGE_URL"
    echo "Storage Directory: $STORAGE_DIR"

    if [ -f "$PID_FILE" ]; then
        if is_running; then
            echo -e "Status: ${GREEN}Running${NC} (PID: $(cat $PID_FILE))"
        else
            echo -e "Status: ${RED}Stopped${NC} (stale PID file)"
        fi
    else
        echo -e "Status: ${YELLOW}Stopped${NC}"
    fi

    # Show studies if available
    if [ "$STORAGE_TYPE" = "sqlite" ] && [ -f "${STORAGE_DIR}/optuna.db" ]; then
        echo ""
        echo "Available studies:"
        python3 -m optuna studies --storage "$STORAGE_URL" 2>/dev/null || echo "No studies found"
    fi
}

# Main command handling
case "${1:-start}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    status)
        show_status
        ;;
    restart)
        stop_server
        sleep 1
        start_server
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        exit 1
        ;;
esac

exit 0
