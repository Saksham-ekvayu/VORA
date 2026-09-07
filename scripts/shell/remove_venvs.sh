#!/bin/bash
# =====================================================
# VORA Backend - Remove Virtual Environments Script
# =====================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../backend" && pwd)"

echo ""
echo "====================================================="
echo "Removing Virtual Environments"
echo "====================================================="
echo ""

python3 "$(dirname "${BASH_SOURCE[0]}")/../remove_venvs.py"

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to remove virtual environments."
    exit 1
fi

echo ""
echo "====================================================="
echo "Virtual environments removed successfully!"
echo "====================================================="
echo ""
