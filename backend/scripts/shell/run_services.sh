#!/bin/bash
# =====================================================
# VORA Backend - Run All Services Script (Parallel)
# =====================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Checking if virtual environments are set up..."
if [ ! -d "$ROOT/gateway/.venv" ]; then
    echo "ERROR: Virtual environments not found. Please run install_venvs.sh first."
    exit 1
fi

echo ""
echo "Starting all services in parallel..."
echo ""

# Function to run a service in background
run_service() {
    local service_name=$1
    local dir=$2
    local app=$3
    
    # Extract PORT from .env
    local port=""
    if [ -f "$ROOT/$dir/.env" ]; then
        port=$(grep '^PORT=' "$ROOT/$dir/.env" | cut -d '=' -f2 | tr -d '\r' | xargs)
    fi
    if [ -z "$port" ]; then
        port=8000 # default fallback
    fi
    
    echo "[$(date '+%H:%M:%S')] Starting $service_name on port $port..."
    
    (
        cd "$ROOT/$dir" || exit 1
        source .venv/bin/activate 2>/dev/null || true
        python3 -m uvicorn "$app" --host localhost --port "$port" --reload --reload-dir . --reload-dir ../../shared 2>&1 | sed "s/^/[$service_name] /"
    ) &
    
    # Store PID for later cleanup
    echo $! >> /tmp/vora_pids.txt
}

# Create PID file
rm -f /tmp/vora_pids.txt
touch /tmp/vora_pids.txt

# Trap to cleanup all services on exit
cleanup() {
    echo ""
    echo "[$(date '+%H:%M:%S')] Stopping all services..."
    if [ -f /tmp/vora_pids.txt ]; then
        while read pid; do
            if kill -0 "$pid" 2>/dev/null; then
                echo "[$(date '+%H:%M:%S')] Killing PID $pid"
                kill "$pid" 2>/dev/null || true
            fi
        done < /tmp/vora_pids.txt
    fi
    rm -f /tmp/vora_pids.txt
}

trap cleanup EXIT INT TERM

# Start all services in parallel (Ports are dynamically read from their .env files)
run_service "authentication-service" "services/authentication-service" "app.main:app"
run_service "profile-service" "services/profile-service" "app.main:app"
run_service "dashboard-service" "services/dashboard-service" "app.main:app"
run_service "framework-category-service" "services/framework-category-service" "app.main:app"
run_service "framework-service" "services/framework-service" "app.main:app"
run_service "deployment-framework-service" "services/deployment-framework-service" "app.main:app"
run_service "extract-controls-service" "services/extract-controls-service" "app.main:app"
run_service "compliance-agent-service" "services/compliance-agent-service" "app.main:app"
run_service "ai-analysis-service" "services/ai-analysis-service" "app.main:app"
run_service "mcp-boto3-server" "services/mcp-boto3-server" "app.main:app"
run_service "api-gateway" "gateway" "main:app"

# Start frontend
echo "[$(date '+%H:%M:%S')] Starting frontend on Vite..."
(
    cd "$ROOT/../frontend" || exit 1
    pnpm dev 2>&1 | sed "s/^/[frontend] /"
) &
echo $! >> /tmp/vora_pids.txt

echo ""
echo "=========================================="
echo "All services started in parallel!"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop all services."
echo "=========================================="
echo ""

# Wait for all background processes
wait
