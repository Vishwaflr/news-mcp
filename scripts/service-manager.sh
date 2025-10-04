#!/bin/bash
# Service Manager for News MCP - Provides supervisor-like functionality
# Usage: ./service-manager.sh [start|stop|restart|status|logs|monitor]

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Service definitions
declare -A SERVICES
SERVICES["api"]="uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"
SERVICES["scheduler"]="python -B app/services/scheduler_runner.py"
SERVICES["worker"]="python -B app/worker/analysis_worker.py --verbose"

# PID file locations
declare -A PID_FILES
PID_FILES["api"]="/tmp/news-mcp-api.pid"
PID_FILES["scheduler"]="/tmp/news-mcp-scheduler.pid"
PID_FILES["worker"]="/tmp/news-mcp-worker.pid"

# Log file locations
declare -A LOG_FILES
LOG_FILES["api"]="logs/api-managed.log"
LOG_FILES["scheduler"]="logs/scheduler-managed.log"
LOG_FILES["worker"]="logs/worker-managed.log"

# Function to check if a service is running
is_running() {
    local service=$1
    local pid_file="${PID_FILES[$service]}"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to start a service
start_service() {
    local service=$1
    local command="${SERVICES[$service]}"
    local pid_file="${PID_FILES[$service]}"
    local log_file="${LOG_FILES[$service]}"

    if is_running "$service"; then
        echo -e "${YELLOW}$service is already running${NC}"
        return
    fi

    echo -e "${BLUE}Starting $service...${NC}"

    # Activate virtual environment
    source venv/bin/activate

    # Load environment variables
    if [ -f ".env" ]; then
        while IFS='=' read -r key value; do
            if [[ ! "$key" =~ ^[[:space:]]*# && -n "$key" ]]; then
                export "$key=$value"
            fi
        done < <(grep -v '^[[:space:]]*#' .env | grep -v '^[[:space:]]*$')
    fi

    # Start service with automatic restart on failure
    (
        while true; do
            $command >> "$log_file" 2>&1 &
            local pid=$!
            echo $pid > "$pid_file"

            # Wait for process to exit
            wait $pid
            local exit_code=$?

            echo "[$(date)] Service $service exited with code $exit_code, restarting..." >> "$log_file"
            sleep 5  # Wait before restart
        done
    ) &

    local monitor_pid=$!
    echo $monitor_pid > "${pid_file}.monitor"

    sleep 2

    if is_running "$service"; then
        echo -e "${GREEN}✓ $service started successfully${NC}"
    else
        echo -e "${RED}✗ Failed to start $service${NC}"
    fi
}

# Function to stop a service
stop_service() {
    local service=$1
    local pid_file="${PID_FILES[$service]}"

    if ! is_running "$service"; then
        echo -e "${YELLOW}$service is not running${NC}"
        return
    fi

    echo -e "${BLUE}Stopping $service...${NC}"

    # Kill the monitor process first
    if [ -f "${pid_file}.monitor" ]; then
        local monitor_pid=$(cat "${pid_file}.monitor")
        kill -TERM "$monitor_pid" 2>/dev/null || true
        rm -f "${pid_file}.monitor"
    fi

    # Kill the actual service
    local pid=$(cat "$pid_file")
    kill -TERM "$pid" 2>/dev/null || true

    # Wait for process to die
    local count=0
    while [ $count -lt 10 ] && ps -p "$pid" > /dev/null 2>&1; do
        sleep 1
        count=$((count + 1))
    done

    # Force kill if still running
    if ps -p "$pid" > /dev/null 2>&1; then
        kill -KILL "$pid" 2>/dev/null || true
    fi

    rm -f "$pid_file"
    echo -e "${GREEN}✓ $service stopped${NC}"
}

# Function to restart a service
restart_service() {
    local service=$1
    stop_service "$service"
    sleep 2
    start_service "$service"
}

# Function to show service status
show_status() {
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}     News MCP Service Status${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""

    for service in api scheduler worker; do
        if is_running "$service"; then
            local pid=$(cat "${PID_FILES[$service]}")
            local mem=$(ps -o rss= -p "$pid" 2>/dev/null | awk '{print int($1/1024)"MB"}')
            local cpu=$(ps -o %cpu= -p "$pid" 2>/dev/null | awk '{print $1"%"}')
            echo -e "$service: ${GREEN}● Running${NC} (PID: $pid, CPU: $cpu, Mem: $mem)"
        else
            echo -e "$service: ${RED}○ Stopped${NC}"
        fi
    done

    echo ""
    echo -e "${BLUE}Database Services (Docker):${NC}"
    if docker ps --format "{{.Names}}" | grep -q "postgres-news"; then
        echo -e "PostgreSQL: ${GREEN}● Running${NC}"
    else
        echo -e "PostgreSQL: ${RED}○ Stopped${NC}"
    fi

    if docker ps --format "{{.Names}}" | grep -q "redis-news"; then
        echo -e "Redis: ${GREEN}● Running${NC}"
    else
        echo -e "Redis: ${RED}○ Stopped${NC}"
    fi
}

# Function to tail logs
show_logs() {
    local service=$1
    local log_file="${LOG_FILES[$service]}"

    if [ -z "$service" ]; then
        # Show all logs
        echo -e "${BLUE}Showing combined logs (Ctrl+C to stop)...${NC}"
        tail -f logs/*.log
    else
        # Show specific service logs
        echo -e "${BLUE}Showing $service logs (Ctrl+C to stop)...${NC}"
        tail -f "$log_file"
    fi
}

# Function to monitor services (auto-restart if needed)
monitor_services() {
    echo -e "${BLUE}Starting service monitor (Ctrl+C to stop)...${NC}"
    echo -e "${YELLOW}Services will auto-restart on failure${NC}"
    echo ""

    while true; do
        for service in api scheduler worker; do
            if ! is_running "$service"; then
                echo -e "${YELLOW}[$(date)] $service is down, restarting...${NC}"
                start_service "$service"
            fi
        done
        sleep 10
    done
}

# Main command handler
case "$1" in
    start)
        if [ -z "$2" ]; then
            # Start all services
            echo -e "${BLUE}Starting all services...${NC}"
            for service in api scheduler worker; do
                start_service "$service"
            done
        else
            start_service "$2"
        fi
        ;;

    stop)
        if [ -z "$2" ]; then
            # Stop all services
            echo -e "${BLUE}Stopping all services...${NC}"
            for service in api scheduler worker; do
                stop_service "$service"
            done
        else
            stop_service "$2"
        fi
        ;;

    restart)
        if [ -z "$2" ]; then
            # Restart all services
            echo -e "${BLUE}Restarting all services...${NC}"
            for service in api scheduler worker; do
                restart_service "$service"
            done
        else
            restart_service "$2"
        fi
        ;;

    status)
        show_status
        ;;

    logs)
        show_logs "$2"
        ;;

    monitor)
        monitor_services
        ;;

    *)
        echo "News MCP Service Manager"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|monitor} [service]"
        echo ""
        echo "Commands:"
        echo "  start [service]    Start service(s)"
        echo "  stop [service]     Stop service(s)"
        echo "  restart [service]  Restart service(s)"
        echo "  status            Show service status"
        echo "  logs [service]    Tail service logs"
        echo "  monitor           Monitor and auto-restart services"
        echo ""
        echo "Services: api, scheduler, worker"
        echo ""
        echo "Examples:"
        echo "  $0 start           # Start all services"
        echo "  $0 stop api        # Stop API service"
        echo "  $0 restart worker  # Restart worker"
        echo "  $0 status          # Show all service status"
        echo "  $0 logs api        # Tail API logs"
        echo "  $0 monitor         # Start monitoring daemon"
        exit 1
        ;;
esac