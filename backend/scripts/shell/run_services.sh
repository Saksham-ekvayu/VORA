#!/bin/bash
# =====================================================
# VORA Backend - Run All Services Script
# =====================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Checking if virtual environments are set up..."
if [ ! -d "$ROOT/gateway/.venv" ]; then
    echo "ERROR: Virtual environments not found. Please run install_venvs.sh first."
    exit 1
fi

echo ""
echo "Starting services in background..."
echo ""

# Function to run a service
run_service() {
    local dir=$1
    local port=$2
    local app=$3
    echo "Starting $dir on port $port..."
    cd "$ROOT/$dir"
    source .venv/bin/activate
    python3 -m uvicorn $app --host localhost --port $port --reload --reload-dir . --reload-dir "$ROOT/shared" &
    deactivate
}

run_service "services/authentication-service" 7001 "app.main:app"
run_service "services/profile-service" 7002 "app.main:app"
run_service "services/dashboard-service" 7003 "app.main:app"
run_service "services/framework-category-service" 7004 "app.main:app"
run_service "services/framework-service" 7005 "app.main:app"
run_service "services/deployment-framework-service" 7006 "app.main:app"
run_service "services/extract-controls-service" 7007 "app.main:app"
run_service "services/compliance-agent-service" 7008 "app.main:app"
run_service "services/ai-analysis-service" 7009 "app.main:app"

echo "Starting api-gateway on port 8000..."
cd "$ROOT/gateway"
source .venv/bin/activate
python3 -m uvicorn main:app --host localhost --port 8000 --reload &
deactivate

echo ""
echo "All services started in background."
echo "Press Ctrl+C to stop all services."
wait
