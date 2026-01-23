#!/bin/bash

# ============================================
# FTA Tariff Processor - Linux/Mac Launcher
# ============================================

echo "========================================"
echo "FTA Tariff Processing System"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed!"
    echo ""
    echo "Please install Python 3.8 or higher:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  macOS: brew install python3"
    echo ""
    exit 1
fi

echo "[INFO] Python detected: $(python3 --version)"
echo ""

# Check if dependencies are installed
python3 -c "import streamlit" &> /dev/null
if [ $? -ne 0 ]; then
    echo "[INFO] First-time setup: Installing dependencies..."
    echo "This may take a few minutes..."
    echo ""
    python3 -m pip install --upgrade pip
    pip3 install -r requirements.txt
    echo ""
    echo "[SUCCESS] Dependencies installed!"
    echo ""
else
    echo "[INFO] Dependencies already installed"
    echo ""
fi

# Create folders if they don't exist
mkdir -p "input XML"
mkdir -p "output_generated"

echo "[INFO] Starting Tariff Processor..."
echo ""
echo "The application will open in your browser."
echo "Press Ctrl+C to stop the application."
echo ""
echo "========================================"
echo ""

# Run Streamlit
streamlit run app.py --server.headless=true
