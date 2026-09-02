#!/bin/bash
# =====================================================
# VORA Backend - Format Code Script
# Uses Black for code formatting and Isort for imports
# =====================================================

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../backend" && pwd)"

echo ""
echo "====================================================="
echo "Formatting VORA Backend Code"
echo "====================================================="
echo ""

echo "[1/3] Ensuring Black and Isort are installed..."
python3 -m pip install --quiet black isort
if [ $? -ne 0 ]; then
    echo "WARNING: Could not install black and isort. Make sure Python is in your PATH."
else
    echo "OK."
fi

cd "$BACKEND_DIR"

echo ""
echo "[2/3] Running Black (Code Formatter)..."
echo "Formatting Python files..."
python3 -m black . --exclude "\.venv|__pycache__" --extend-exclude "\.ipynb"
if [ $? -ne 0 ]; then
    echo "ERROR: Black formatting failed."
    exit 1
fi
echo "OK."

echo ""
echo "[3/3] Running Isort (Import Sorter)..."
echo "Sorting imports in Python files..."
python3 -m isort . --skip-gitignore --skip ".venv"
if [ $? -ne 0 ]; then
    echo "ERROR: Isort formatting failed."
    exit 1
fi
echo "OK."

echo ""
echo "====================================================="
echo "Formatting Complete!"
echo "====================================================="
echo ""
echo "All Python files in backend have been formatted."
echo ""
