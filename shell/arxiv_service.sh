#!/bin/bash
# arXiv RAG API Service Management Script
#
# Usage:
#   ./arxiv_service.sh [start|stop|restart|status]
#   Default: restart

set -e

# Get script and project directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ============ 用户配置区 ============
# 请根据实际情况修改以下变量
CONDA_ENV="arxiv_rag"  # 修改为你的conda环境名
# ==================================

# Configuration
PID_FILE="$PROJECT_ROOT/logs/api.pid"
LOG_FILE="$PROJECT_ROOT/logs/api.log"
ERR_FILE="$PROJECT_ROOT/logs/api.err"
API_PORT=5001
HEALTH_CHECK_URL="http://localhost:$API_PORT/api/v1/health"

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if process is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Health check function
health_check() {
    if command -v curl &> /dev/null; then
        if curl -s "$HEALTH_CHECK_URL" | grep -q "ok"; then
            return 0
        fi
    fi
    return 1
}

# Health check with timeout
health_check_with_timeout() {
    local timeout=$1
    local elapsed=0

    echo "Waiting for service to be healthy (timeout: ${timeout}s)..."

    while [ $elapsed -lt $timeout ]; do
        if health_check; then
            print_success "Service is healthy!"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
        echo -n "."
    done

    echo
    print_error "Health check failed after ${timeout}s"
    print_warning "Check logs for details:"
    print_warning "  tail -f $LOG_FILE"
    print_warning "  tail -f $ERR_FILE"
    return 1
}

# Start service
start() {
    if is_running; then
        print_warning "Service is already running (PID: $(cat $PID_FILE))"
        return 0
    fi

    echo "Starting arXiv RAG API service..."

    # Activate conda environment
    eval "$(conda shell.bash hook)"
    conda activate "$CONDA_ENV" || {
        print_error "Failed to activate conda environment: $CONDA_ENV"
        return 1
    }

    # Start service in background
    cd "$PROJECT_ROOT"
    nohup python scripts/run_api.py > "$LOG_FILE" 2> "$ERR_FILE" &
    PID=$!
    echo $PID > "$PID_FILE"

    print_success "Service started (PID: $PID)"

    # Health check
    if health_check_with_timeout 30; then
        print_success "Service is ready!"
        echo "Swagger UI: http://localhost:$API_PORT/docs"
        return 0
    else
        print_error "Service started but health check failed"
        return 1
    fi
}

# Stop service
stop() {
    if ! is_running; then
        print_warning "Service is not running"
        rm -f "$PID_FILE"
        return 0
    fi

    PID=$(cat "$PID_FILE")
    echo "Stopping service (PID: $PID)..."

    # Try graceful shutdown first
    kill "$PID" 2>/dev/null || true

    # Wait for process to stop (max 10 seconds)
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            print_success "Service stopped"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
    done

    # Force kill if still running
    print_warning "Graceful shutdown failed, forcing..."
    kill -9 "$PID" 2>/dev/null || true
    rm -f "$PID_FILE"
    print_success "Service stopped (forced)"
}

# Restart service
restart() {
    echo "Restarting service..."
    stop
    sleep 2
    start
}

# Status
status() {
    echo "==================================================="
    echo "arXiv RAG API Service Status"
    echo "==================================================="

    if is_running; then
        PID=$(cat "$PID_FILE")
        print_success "Service is running (PID: $PID)"

        # Check health
        if health_check; then
            print_success "Health check: PASSED"
        else
            print_warning "Health check: FAILED"
        fi

        # Show process info
        echo
        echo "Process info:"
        ps -p "$PID" -o pid,ppid,%cpu,%mem,etime,cmd 2>/dev/null || echo "  (process info unavailable)"

        # Check port
        echo
        echo "Port status:"
        if command -v netstat &> /dev/null; then
            netstat -tuln | grep ":$API_PORT " || echo "  Port $API_PORT not listening"
        elif command -v ss &> /dev/null; then
            ss -tuln | grep ":$API_PORT " || echo "  Port $API_PORT not listening"
        else
            echo "  (port checking tools not available)"
        fi

        # Show recent logs
        echo
        echo "Recent logs (last 10 lines):"
        if [ -f "$LOG_FILE" ]; then
            tail -n 10 "$LOG_FILE" | sed 's/^/  /'
        else
            echo "  (no logs)"
        fi

    else
        print_error "Service is not running"

        # Check for stale PID file
        if [ -f "$PID_FILE" ]; then
            print_warning "Stale PID file found: $PID_FILE"
            rm -f "$PID_FILE"
            print_success "Cleaned up stale PID file"
        fi
    fi

    echo "==================================================="
    echo
    echo "Useful commands:"
    echo "  View logs:   tail -f $LOG_FILE"
    echo "  View errors: tail -f $ERR_FILE"
    echo "  Swagger UI:  http://localhost:$API_PORT/docs"
}

# Build database
build_data() {
    local mode="${1:-all}"
    local max_results="${2:--1}"

    echo "Building database..."

    # Activate conda environment
    eval "$(conda shell.bash hook)"
    conda activate "$CONDA_ENV" || {
        print_error "Failed to activate conda environment: $CONDA_ENV"
        return 1
    }

    cd "$PROJECT_ROOT"

    if [ "$mode" = "fetch" ]; then
        print_success "Build mode: fetch (爬取到CSV)"
        python scripts/run_builder.py build --mode fetch --max-results "$max_results"
    elif [ "$mode" = "embed" ]; then
        print_success "Build mode: embed (从CSV嵌入)"
        python scripts/run_builder.py build --mode embed
    else
        print_success "Build mode: all (完整流程)"
        python scripts/run_builder.py build --mode all --max-results "$max_results"
    fi
}

# Update database
update_data() {
    local mode="${1:-all}"
    local max_results="${2:-100}"
    local csv_file="${3:-}"

    echo "Updating database..."

    # Activate conda environment
    eval "$(conda shell.bash hook)"
    conda activate "$CONDA_ENV" || {
        print_error "Failed to activate conda environment: $CONDA_ENV"
        return 1
    }

    cd "$PROJECT_ROOT"

    if [ "$mode" = "fetch" ]; then
        print_success "Update mode: fetch (增量爬取到CSV)"
        python scripts/run_builder.py update --mode fetch --max-results "$max_results"
    elif [ "$mode" = "embed" ]; then
        print_success "Update mode: embed (从CSV嵌入)"
        if [ -n "$csv_file" ]; then
            python scripts/run_builder.py update --mode embed --csv "$csv_file"
        else
            python scripts/run_builder.py update --mode embed
        fi
    else
        print_success "Update mode: all (完整流程)"
        python scripts/run_builder.py update --mode all --max-results "$max_results"
    fi
}

# List CSV files
list_csvs() {
    echo "Listing daily CSV files..."

    # Activate conda environment
    eval "$(conda shell.bash hook)"
    conda activate "$CONDA_ENV" || {
        print_error "Failed to activate conda environment: $CONDA_ENV"
        return 1
    }

    cd "$PROJECT_ROOT"
    python scripts/run_builder.py list-csv
}

# Main command handler
case "${1:-restart}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    health)
        if health_check; then
            print_success "Service is healthy"
            exit 0
        else
            print_error "Service is unhealthy"
            exit 1
        fi
        ;;
    logs)
        tail -f "$LOG_FILE"
        ;;
    build)
        # Usage: ./arxiv_service.sh build [fetch|embed|all] [max_results]
        build_data "${2:-all}" "${3:--1}"
        ;;
    update)
        # Usage: ./arxiv_service.sh update [fetch|embed|all] [max_results] [csv_file]
        update_data "${2:-all}" "${3:-100}" "${4:-}"
        ;;
    list)
        list_csvs
        ;;
    *)
        echo "Usage: $0 [start|stop|restart|status|health|logs|build|update|list]"
        echo
        echo "Service commands:"
        echo "  start         - Start the API service"
        echo "  stop          - Stop the API service"
        echo "  restart       - Restart the API service (default)"
        echo "  status        - Show API service status"
        echo "  health        - Check API service health"
        echo "  logs          - Follow API service logs"
        echo
        echo "Data management commands:"
        echo "  build [mode] [max]      - Build database from scratch"
        echo "                            mode: fetch|embed|all (default: all)"
        echo "                            max: max results (default: -1 unlimited)"
        echo "                            Examples:"
        echo "                              ./arxiv_service.sh build all"
        echo "                              ./arxiv_service.sh build fetch 1000"
        echo "                              ./arxiv_service.sh build embed"
        echo
        echo "  update [mode] [max] [csv] - Incremental update"
        echo "                            mode: fetch|embed|all (default: all)"
        echo "                            max: max results (default: 100)"
        echo "                            csv: CSV file for embed mode (optional)"
        echo "                            Examples:"
        echo "                              ./arxiv_service.sh update all"
        echo "                              ./arxiv_service.sh update fetch 50"
        echo "                              ./arxiv_service.sh update embed"
        echo "                              ./arxiv_service.sh update embed 100 daily/20260109.csv"
        echo
        echo "  list          - List all daily CSV files"
        exit 1
        ;;
esac
