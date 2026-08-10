#!/bin/bash
# =====================================================
# VORA Backend - Run All Services Script (Tabbed Version)
# =====================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Checking if virtual environments are set up..."
if [ ! -d "$ROOT/gateway/.venv" ]; then
    echo "ERROR: Virtual environments not found. Please run install_venvs.sh first."
    exit 1
fi

echo ""
echo "Starting services..."
echo ""

# ---------------------------------------------------------
# 1. Windows Terminal (wt.exe) for Git Bash / WSL on Windows
# ---------------------------------------------------------
if command -v wt.exe &> /dev/null; then
    echo "Windows Terminal found. Opening services in separate tabs..."
    
    # Convert ROOT to Windows path if running in Git Bash or WSL
    if command -v cygpath &> /dev/null; then
        WIN_ROOT=$(cygpath -w "$ROOT")
    elif command -v wslpath &> /dev/null; then
        WIN_ROOT=$(wslpath -w "$ROOT")
    else
        WIN_ROOT="$ROOT"
    fi

    wt.exe -w new \
        new-tab --title "authentication-service (7001)" -d "$WIN_ROOT/services/authentication-service" bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7001 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        \; new-tab --title "profile-service (7002)" -d "$WIN_ROOT/services/profile-service" bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7002 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        \; new-tab --title "dashboard-service (7003)" -d "$WIN_ROOT/services/dashboard-service" bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7003 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        \; new-tab --title "framework-category-service (7004)" -d "$WIN_ROOT/services/framework-category-service" bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7004 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        \; new-tab --title "framework-service (7005)" -d "$WIN_ROOT/services/framework-service" bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7005 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        \; new-tab --title "deployment-framework-service (7006)" -d "$WIN_ROOT/services/deployment-framework-service" bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7006 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        \; new-tab --title "extract-controls-service (7007)" -d "$WIN_ROOT/services/extract-controls-service" bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7007 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        \; new-tab --title "compliance-agent-service (7008)" -d "$WIN_ROOT/services/compliance-agent-service" bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7008 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        \; new-tab --title "ai-analysis-service (7009)" -d "$WIN_ROOT/services/ai-analysis-service" bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7009 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        \; new-tab --title "api-gateway (8000)" -d "$WIN_ROOT/gateway" bash -c "source .venv/bin/activate && python3 -m uvicorn main:app --host localhost --port 8000 --reload; exec bash"
    
    echo "All services started in Windows Terminal tabs."
    exit 0

# ---------------------------------------------------------
# 2. GNOME Terminal for Linux
# ---------------------------------------------------------
elif command -v gnome-terminal &> /dev/null; then
    echo "gnome-terminal found. Opening services in separate tabs..."
    
    gnome-terminal \
        --tab --title="authentication-service (7001)" --working-directory="$ROOT/services/authentication-service" -- bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7001 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        --tab --title="profile-service (7002)" --working-directory="$ROOT/services/profile-service" -- bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7002 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        --tab --title="dashboard-service (7003)" --working-directory="$ROOT/services/dashboard-service" -- bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7003 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        --tab --title="framework-category-service (7004)" --working-directory="$ROOT/services/framework-category-service" -- bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7004 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        --tab --title="framework-service (7005)" --working-directory="$ROOT/services/framework-service" -- bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7005 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        --tab --title="deployment-framework-service (7006)" --working-directory="$ROOT/services/deployment-framework-service" -- bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7006 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        --tab --title="extract-controls-service (7007)" --working-directory="$ROOT/services/extract-controls-service" -- bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7007 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        --tab --title="compliance-agent-service (7008)" --working-directory="$ROOT/services/compliance-agent-service" -- bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7008 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        --tab --title="ai-analysis-service (7009)" --working-directory="$ROOT/services/ai-analysis-service" -- bash -c "source .venv/bin/activate && python3 -m uvicorn app.main:app --host localhost --port 7009 --reload --reload-dir . --reload-dir ../../shared; exec bash" \
        --tab --title="api-gateway (8000)" --working-directory="$ROOT/gateway" -- bash -c "source .venv/bin/activate && python3 -m uvicorn main:app --host localhost --port 8000 --reload; exec bash"
    
    echo "All services started in gnome-terminal tabs."
    exit 0

# ---------------------------------------------------------
# 3. macOS Terminal
# ---------------------------------------------------------
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macOS detected. Opening services in new Terminal windows..."
    
    run_service_mac() {
        local dir=$1
        local port=$2
        local app=$3
        osascript -e "tell application \"Terminal\" to do script \"cd '$ROOT/$dir' && source .venv/bin/activate && python3 -m uvicorn $app --host localhost --port $port --reload --reload-dir . --reload-dir '../../shared'\""
    }
    
    run_service_mac "services/authentication-service" 7001 "app.main:app"
    run_service_mac "services/profile-service" 7002 "app.main:app"
    run_service_mac "services/dashboard-service" 7003 "app.main:app"
    run_service_mac "services/framework-category-service" 7004 "app.main:app"
    run_service_mac "services/framework-service" 7005 "app.main:app"
    run_service_mac "services/deployment-framework-service" 7006 "app.main:app"
    run_service_mac "services/extract-controls-service" 7007 "app.main:app"
    run_service_mac "services/compliance-agent-service" 7008 "app.main:app"
    run_service_mac "services/ai-analysis-service" 7009 "app.main:app"
    run_service_mac "gateway" 8000 "main:app"
    
    echo "All services started in new Terminal windows."
    exit 0

# ---------------------------------------------------------
# 4. Fallback (Background execution in same terminal)
# ---------------------------------------------------------
else
    echo "No supported terminal multiplexer (wt.exe, gnome-terminal, macOS) found."
    echo "Falling back to running services in the background of the current terminal..."
    
    run_service() {
        local dir=$1
        local port=$2
        local app=$3
        echo "Starting $dir on port $port..."
        cd "$ROOT/$dir"
        source .venv/bin/activate
        python3 -m uvicorn $app --host localhost --port $port --reload --reload-dir . --reload-dir "$ROOT/shared" &
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

    echo ""
    echo "All services started in background."
    echo "Press Ctrl+C to stop all services."
    wait
fi
