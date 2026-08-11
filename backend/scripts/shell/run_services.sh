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
    local port=$2
    local dir=$3
    local app=$4
    
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

# Start all services in parallel
run_service "authentication-service" 7001 "services/authentication-service" "app.main:app"
run_service "profile-service" 7002 "services/profile-service" "app.main:app"
run_service "dashboard-service" 7003 "services/dashboard-service" "app.main:app"
run_service "framework-category-service" 7004 "services/framework-category-service" "app.main:app"
run_service "framework-service" 7005 "services/framework-service" "app.main:app"
run_service "deployment-framework-service" 7006 "services/deployment-framework-service" "app.main:app"
run_service "extract-controls-service" 7007 "services/extract-controls-service" "app.main:app"
run_service "compliance-agent-service" 7008 "services/compliance-agent-service" "app.main:app"
run_service "ai-analysis-service" 7009 "services/ai-analysis-service" "app.main:app"
run_service "api-gateway" 8000 "gateway" "main:app"

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
echo "Service Ports:"
echo "  - authentication-service: http://localhost:7001"
echo "  - profile-service: http://localhost:7002"
echo "  - dashboard-service: http://localhost:7003"
echo "  - framework-category-service: http://localhost:7004"
echo "  - framework-service: http://localhost:7005"
echo "  - deployment-framework-service: http://localhost:7006"
echo "  - extract-controls-service: http://localhost:7007"
echo "  - compliance-agent-service: http://localhost:7008"
echo "  - ai-analysis-service: http://localhost:7009"
echo "  - api-gateway: http://localhost:8000"
echo "  - frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all services."
echo "=========================================="
echo ""

# Wait for all background processes
wait
