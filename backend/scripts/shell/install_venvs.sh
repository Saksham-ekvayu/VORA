#!/bin/bash
# =====================================================
# VORA Backend - Install Virtual Environments Script
# =====================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo ""
echo "====================================================="
echo "Installing VORA Backend Virtual Environments"
echo "====================================================="
echo ""

if [ ! -d "$ROOT/shared" ]; then
    echo "WARNING: Shared directory not found at $ROOT/shared"
    echo "Skipping shared package installation."
else
    echo "[1/3] Installing shared package..."
    cd "$ROOT/shared"
    python3 -m pip install -e .
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install shared package."
        exit 1
    fi
    echo "OK."
fi

echo ""
echo "[2/3] Creating virtual environments for all services..."
cd "$ROOT"
python3 scripts/create_venvs.py
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environments."
    exit 1
fi
echo "OK."

echo ""
echo "[3/3] Installing dependencies in each service sequentially..."
echo ""

SERVICES=(
    "authentication-service"
    "profile-service"
    "dashboard-service"
    "framework-category-service"
    "framework-service"
    "deployment-framework-service"
    "extract-controls-service"
    "compliance-agent-service"
    "ai-analysis-service"
    "mcp-boto3-server"
)

for service in "${SERVICES[@]}"; do
    echo "Installing $service dependencies..."
    cd "$ROOT/services/$service"
    source .venv/bin/activate
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR installing $service dependencies."
    fi
    deactivate
done

echo "Installing api-gateway dependencies..."
cd "$ROOT/gateway"
source .venv/bin/activate
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR installing gateway dependencies."
fi
deactivate

echo ""
echo "====================================================="
echo "All services installed successfully!"
echo "====================================================="
echo ""
echo "Next steps:"
echo "1. Run run_services.sh to start all services"
echo "2. Access the API Gateway at: http://localhost:8000"
echo ""
