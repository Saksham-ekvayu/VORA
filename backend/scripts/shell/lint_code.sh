#!/bin/bash
# =====================================================
# VORA Backend - Lint Code Script
# Uses Ruff for blazing fast code linting
# =====================================================

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo ""
echo "====================================================="
echo "Linting VORA Backend Code"
echo "====================================================="
echo ""

echo "[1/2] Ensuring Ruff is installed..."
python3 -m pip install --quiet ruff
if [ $? -ne 0 ]; then
    echo "WARNING: Could not install ruff. Make sure Python is in your PATH."
else
    echo "OK."
fi

cd "$BACKEND_DIR"

echo ""
echo "[2/2] Running Ruff Linter..."
echo "Linting Python files..."
python3 -m ruff check .
if [ $? -ne 0 ]; then
    echo "ERROR: Linter found issues in the code."
    exit 1
fi
echo "OK. No linting issues found!"

echo ""
echo "====================================================="
echo "Linting Complete!"
echo "====================================================="
echo ""
