#!/bin/bash
# =====================================================
# VORA Backend - Lint Code Script
# Uses Ruff or Pylint based on user selection
# =====================================================

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo ""
echo "====================================================="
echo "Linting VORA Backend Code"
echo "====================================================="
echo ""

echo "Select the linter you want to use:"
echo "[A] Ruff (Blazing fast, modern standard)"
echo "[B] Pylint (Deep static analysis, strict)"
echo ""

read -p "Enter your choice (A/B): " choice

case "$choice" in 
  a|A )
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
    ;;
  b|B )
    echo ""
    echo "[1/2] Ensuring Pylint is installed..."
    python3 -m pip install --quiet pylint
    if [ $? -ne 0 ]; then
        echo "WARNING: Could not install pylint. Make sure Python is in your PATH."
    else
        echo "OK."
    fi

    cd "$BACKEND_DIR"

    echo ""
    echo "[2/2] Running Pylint Linter..."
    echo "Linting Python files..."
    # Pylint works best when pointed at packages/modules, ignore virtual envs and use multi-processing
    python3 -m pylint services shared gateway scripts --ignore=.venv,__pycache__ -j 0
    if [ $? -ne 0 ]; then
        echo "ERROR: Linter found issues in the code."
        exit 1
    fi
    echo "OK. No linting issues found!"
    ;;
  * )
    echo "Invalid choice. Please run the script again and select A or B."
    exit 1
    ;;
esac

echo ""
echo "====================================================="
echo "Linting Complete!"
echo "====================================================="
echo ""
