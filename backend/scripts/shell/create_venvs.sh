#!/bin/bash
# =====================================================
# VORA Backend - Create Virtual Environments Script
# =====================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo ""
echo "====================================================="
echo "Creating Virtual Environments"
echo "====================================================="
echo ""

python3 "$ROOT/scripts/create_venvs.py"

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to create virtual environments."
    exit 1
fi

echo ""
echo "====================================================="
echo "Virtual environments created successfully!"
echo "====================================================="
echo ""
echo "Next step: Run install_venvs.sh to install dependencies"
echo ""
