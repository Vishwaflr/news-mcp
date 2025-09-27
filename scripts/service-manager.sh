#!/bin/bash

# News MCP Service Manager
# Unified interface for managing all News MCP services
# Handles dependencies, health checks, and process groups

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$PROJECT_ROOT/venv"
PYTHON_PATH="$VENV_PATH/bin/python"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_header() {
    echo -e "${PURPLE}🎯 $1${NC}"
    echo -e "${PURPLE}$(printf '%.0s=' {1..50})${NC}"
}

# Check if virtual environment exists
check_venv() {
    if [[ ! -d "$VENV_PATH" ]]; then
        log_error "Virtual environment not found at $VENV_PATH"
        log_info "Please set up the virtual environment first:"
        log_info "  python3 -m venv venv"
        log_info "  source venv/bin/activate"
        log_info "  pip install -r requirements.txt"
        exit 1
    fi

    if [[ ! -f "$PYTHON_PATH" ]]; then
        log_error "Python binary not found in virtual environment"
        exit 1
    fi
}

# Run Python command with proper environment
run_python() {
    local cmd="$1"
    cd "$PROJECT_ROOT"
    export PYTHONPATH="$PROJECT_ROOT"
    source "$VENV_PATH/bin/activate"
    $PYTHON_PATH -c "$cmd"
}

# Start all services
cmd_start() {
    log_header "Starting News MCP Services"

    check_venv

    local services_arg=""
    if [[ -n "$1" ]]; then
        services_arg="services=[\"$1\"]"
        shift
        for service in "$@"; do
            services_arg="$services_arg, \"$service\""
        done
        services_arg="services=[$services_arg]"
    fi

    local python_cmd="
import asyncio
import sys
from app.core.process_manager import ServiceProcessManager

async def main():
    manager = ServiceProcessManager('$PROJECT_ROOT')

    services = None
    if '$services_arg':
        $services_arg

    success = await manager.start_all_services(services)

    if success:
        print('🚀 All services started successfully!')
        return 0
    else:
        print('❌ Failed to start services')
        return 1

if __name__ == '__main__':
    exit(asyncio.run(main()))
"

    if run_python "$python_cmd"; then
        log_success "Services started successfully"
        log_info "Use '$0 status' to check service status"
        log_info "Use '$0 logs' to view service logs"
        return 0
    else
        log_error "Failed to start services"
        return 1
    fi
}

# Stop all services
cmd_stop() {
    log_header "Stopping News MCP Services"

    check_venv

    local python_cmd="
import asyncio
from app.core.process_manager import ServiceProcessManager

async def main():
    manager = ServiceProcessManager('$PROJECT_ROOT')
    success = await manager.stop_all_services()

    if success:
        print('🛑 All services stopped successfully!')
        return 0
    else:
        print('⚠️  Some services may not have stopped cleanly')
        return 1

if __name__ == '__main__':
    exit(asyncio.run(main()))
"

    if run_python "$python_cmd"; then
        log_success "Services stopped successfully"

        # Clean up any remaining PID files
        log_info "Cleaning up PID files..."
        rm -f "$PROJECT_ROOT"/.*.pid

        return 0
    else
        log_warning "Some services may not have stopped cleanly"
        return 1
    fi
}

# Restart services
cmd_restart() {
    log_header "Restarting News MCP Services"

    if [[ -n "$1" ]]; then
        # Restart specific service
        log_info "Restarting service: $1"

        local python_cmd="
import asyncio
from app.core.process_manager import ServiceProcessManager

async def main():
    manager = ServiceProcessManager('$PROJECT_ROOT')
    success = await manager.restart_service('$1')

    if success:
        print('🔄 Service restarted successfully!')
        return 0
    else:
        print('❌ Failed to restart service')
        return 1

if __name__ == '__main__':
    exit(asyncio.run(main()))
"

        run_python "$python_cmd"
    else
        # Restart all services
        log_info "Restarting all services..."
        cmd_stop
        sleep 2
        cmd_start
    fi
}

# Show service status
cmd_status() {
    log_header "News MCP Service Status"

    check_venv

    local python_cmd="
import asyncio
import json
from app.core.process_manager import ServiceProcessManager
from app.core.service_registry import ServiceStatus

async def main():
    manager = ServiceProcessManager('$PROJECT_ROOT')
    status = await manager.get_all_status()

    print(f'{'Service':<20} {'Status':<12} {'Type':<12} {'PID':<8} {'Critical':<8}')
    print('─' * 70)

    for service_id, info in status.items():
        status_icon = {
            'running': '🟢',
            'stopped': '🔴',
            'starting': '🟡',
            'stopping': '🟡',
            'error': '❌',
            'unknown': '❔'
        }.get(info['status'], '❔')

        critical = '⚠️' if info['critical'] else '📎'
        pid = str(info.get('pid', '-'))

        print(f'{info[\"name\"]:<20} {status_icon} {info[\"status\"]:<10} {info[\"type\"]:<12} {pid:<8} {critical:<8}')

    return 0

if __name__ == '__main__':
    exit(asyncio.run(main()))
"

    run_python "$python_cmd"
}

# Run health checks
cmd_health() {
    log_header "News MCP Health Check"

    check_venv

    local python_cmd="
import asyncio
from app.core.process_manager import ServiceProcessManager

async def main():
    manager = ServiceProcessManager('$PROJECT_ROOT')
    health = await manager.health_check_all()

    all_healthy = True

    for service_id, is_healthy in health.items():
        status_icon = '🟢' if is_healthy else '🔴'
        status_text = 'HEALTHY' if is_healthy else 'UNHEALTHY'
        print(f'{service_id:<20} {status_icon} {status_text}')
        if not is_healthy:
            all_healthy = False

    print()
    if all_healthy:
        print('✅ All services are healthy!')
        return 0
    else:
        print('❌ Some services are unhealthy!')
        return 1

if __name__ == '__main__':
    exit(asyncio.run(main()))
"

    run_python "$python_cmd"
}

# Show logs
cmd_logs() {
    local service="$1"
    local follow="$2"

    log_header "News MCP Service Logs"

    local logs_dir="$PROJECT_ROOT/logs"

    if [[ ! -d "$logs_dir" ]]; then
        log_error "Logs directory not found: $logs_dir"
        exit 1
    fi

    if [[ -n "$service" ]]; then
        # Show specific service log
        local log_file="$logs_dir/${service}.log"
        if [[ ! -f "$log_file" ]]; then
            # Try alternative naming
            case "$service" in
                "web-server"|"web"|"server")
                    log_file="$logs_dir/web-server.log"
                    ;;
                "scheduler"|"feeds")
                    log_file="$logs_dir/scheduler.log"
                    ;;
                "worker"|"analysis")
                    log_file="$logs_dir/analysis-worker.log"
                    ;;
                "mcp"|"mcp-server")
                    log_file="$logs_dir/mcp-http.log"
                    ;;
            esac
        fi

        if [[ -f "$log_file" ]]; then
            if [[ "$follow" == "-f" || "$follow" == "--follow" ]]; then
                log_info "Following log: $log_file (Press Ctrl+C to exit)"
                tail -f "$log_file"
            else
                log_info "Showing last 50 lines of: $log_file"
                tail -50 "$log_file"
            fi
        else
            log_error "Log file not found: $log_file"
            exit 1
        fi
    else
        # Show all logs
        if [[ "$follow" == "-f" || "$follow" == "--follow" ]]; then
            log_info "Following all logs (Press Ctrl+C to exit)"
            tail -f "$logs_dir"/*.log 2>/dev/null || {
                log_warning "No log files found in $logs_dir"
                exit 1
            }
        else
            log_info "Available log files:"
            ls -la "$logs_dir"/*.log 2>/dev/null || {
                log_warning "No log files found in $logs_dir"
                exit 1
            }
            echo ""
            log_info "Use '$0 logs <service-name>' to view specific service logs"
            log_info "Use '$0 logs <service-name> -f' to follow logs"
        fi
    fi
}

# Show help
cmd_help() {
    cat << EOF
News MCP Service Manager

USAGE:
    $0 <command> [options]

COMMANDS:
    start [service...]    Start all services or specific services
    stop                  Stop all services
    restart [service]     Restart all services or a specific service
    status                Show status of all services
    health                Run health checks on all services
    logs [service] [-f]   Show logs (optionally follow with -f)
    help                  Show this help message

EXAMPLES:
    $0 start                    # Start all services
    $0 start web-server         # Start only web server
    $0 restart scheduler        # Restart only scheduler
    $0 logs web-server -f       # Follow web server logs
    $0 health                   # Check health of all services

SERVICES:
    web-server               Web server (port 8000)
    scheduler                Feed scheduler
    worker                   Analysis worker
    mcp-server              MCP HTTP server (port 8001)

LOG FILES:
    logs/web-server.log         Web server logs
    logs/scheduler.log          Scheduler logs
    logs/analysis-worker.log    Worker logs
    logs/mcp-http.log          MCP server logs

For more information, see the documentation in docs/ directory.
EOF
}

# Main command dispatcher
main() {
    local command="$1"
    shift || true

    case "$command" in
        start)
            cmd_start "$@"
            ;;
        stop)
            cmd_stop "$@"
            ;;
        restart)
            cmd_restart "$@"
            ;;
        status)
            cmd_status "$@"
            ;;
        health)
            cmd_health "$@"
            ;;
        logs)
            cmd_logs "$@"
            ;;
        help|--help|-h)
            cmd_help
            ;;
        "")
            log_error "No command specified"
            echo ""
            cmd_help
            exit 1
            ;;
        *)
            log_error "Unknown command: $command"
            echo ""
            cmd_help
            exit 1
            ;;
    esac
}

# Trap signals for cleanup
trap 'log_info "Received interrupt signal"; exit 130' INT
trap 'log_info "Received termination signal"; exit 143' TERM

# Run main function
main "$@"