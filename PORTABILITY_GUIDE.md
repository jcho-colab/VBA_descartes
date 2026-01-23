# Portability Guide - FTA Tariff Processing System

## 📦 Making the Application Portable

Yes, this application **can be packaged into an executable (.exe)** for Windows distribution! Here are several approaches:

---

## Option 1: PyInstaller (Recommended for Streamlit)

### Prerequisites
```bash
pip install pyinstaller
```

### Create Executable

#### For Streamlit App (GUI)
```bash
# Create standalone executable
pyinstaller --onefile --add-data "src:src" --hidden-import=streamlit --hidden-import=pandas --hidden-import=lxml --hidden-import=openpyxl app.py

# The executable will be in dist/app.exe
```

#### For Command-Line Version
```bash
pyinstaller --onefile --add-data "src:src" test_run.py
```

### Important Notes for PyInstaller:
1. **Include all dependencies**: The `--hidden-import` flags ensure all modules are bundled
2. **Add data files**: The `--add-data` flag includes the src folder
3. **Excel file**: Must be distributed separately or bundled with `--add-data "HS_IMP_v6.3.xlsm:."`

---

## Option 2: Create Portable Python Distribution

### Using PyOxidizer (Better for Complex Apps)

1. **Install PyOxidizer**:
```bash
cargo install pyoxidizer
```

2. **Create configuration**:
```bash
pyoxidizer init-config-file myapp
```

3. **Build**:
```bash
pyoxidizer build
```

### Advantages:
- More reliable for complex dependencies
- Better handling of Streamlit
- Cross-platform support

---

## Option 3: Docker Container (Most Portable)

### Create Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
```

### Build and Run:
```bash
# Build
docker build -t fta-tariff-processor .

# Run
docker run -p 8501:8501 -v ./input:/app/input -v ./output:/app/output fta-tariff-processor
```

### Advantages:
- **Most portable** - runs anywhere Docker is installed
- **Consistent environment**
- **Easy deployment**

---

## Option 4: Python Embedded Distribution (Standalone Folder)

### Steps:

1. **Download Python Embedded**:
   - Go to https://www.python.org/downloads/windows/
   - Download "Windows embeddable package (64-bit)"

2. **Setup Structure**:
```
FTA_Tariff_Processor/
├── python/                 # Embedded Python
├── src/                    # Your source code
├── app.py
├── HS_IMP_v6.3.xlsm
├── input/
├── output/
├── requirements.txt
└── run.bat                 # Launcher script
```

3. **Create run.bat**:
```batch
@echo off
cd /d "%~dp0"
python\python.exe -m pip install -r requirements.txt --target python\Lib\site-packages
python\python.exe -m streamlit run app.py
pause
```

4. **Distribute**:
   - Zip the entire folder
   - Users just extract and run `run.bat`

### Advantages:
- **No installation required**
- **Works offline**
- **Simple for end users**

---

## 🔧 Recommended Approach for Your Use Case

### For Internal Use (Recommended):

**Use Docker** because:
1. ✅ Easy to deploy across different machines
2. ✅ Consistent environment
3. ✅ Handles all dependencies
4. ✅ Excel file can be mounted as volume
5. ✅ Easy updates (just rebuild image)

### For External Distribution:

**Use Embedded Python + Batch Script** because:
1. ✅ No installation required
2. ✅ Users don't need technical knowledge
3. ✅ Works offline
4. ✅ Can include Excel config file
5. ✅ Simple troubleshooting

---

## 📋 Pre-Packaged Distribution Checklist

Before creating an executable, ensure:

### ✅ Code Changes for Portability

1. **Make paths relative**:
```python
import os
from pathlib import Path

# Get application directory
APP_DIR = Path(__file__).parent

# Use relative paths
config_path = APP_DIR / "HS_IMP_v6.3.xlsm"
input_dir = APP_DIR / "input XML"
output_dir = APP_DIR / "output_generated"
```

2. **Remove hardcoded paths** (Already done in our fixes!)
3. **Bundle configuration file**
4. **Add error handling for missing files**

### ✅ Files to Include

- `app.py` - Main Streamlit application
- `src/` folder - All Python modules
- `requirements.txt` - Dependencies
- `HS_IMP_v6.3.xlsm` - Configuration Excel file
- `README.md` - Usage instructions
- Sample XML files (optional)

### ✅ Dependencies

All dependencies are already in `requirements.txt`:
```
pandas>=1.5.0
streamlit>=1.28.0
lxml>=4.9.0
openpyxl>=3.1.0
pytest>=7.4.0
python-dateutil>=2.8.0
```

---

## 🚀 Quick Start Scripts

### For Windows Users (No Python Installed)

Create `SETUP_AND_RUN.bat`:
```batch
@echo off
echo ============================================
echo FTA Tariff Processor - First Time Setup
echo ============================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed!
    echo Please install Python 3.8+ from https://www.python.org
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Run application
echo Starting application...
streamlit run app.py

pause
```

### For Linux/Mac Users

Create `setup_and_run.sh`:
```bash
#!/bin/bash

echo "============================================"
echo "FTA Tariff Processor - First Time Setup"
echo "============================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Run application
echo "Starting application..."
streamlit run app.py
```

Make executable:
```bash
chmod +x setup_and_run.sh
```

---

## 📦 Creating a Complete Portable Package

### Step-by-Step:

1. **Create package structure**:
```bash
mkdir FTA_Tariff_Processor_Portable
cd FTA_Tariff_Processor_Portable

# Copy application files
cp -r /app/src .
cp /app/app.py .
cp /app/requirements.txt .
cp /app/HS_IMP_v6.3.xlsm .

# Create folders
mkdir "input XML"
mkdir output_generated
```

2. **Add launcher scripts** (see above)

3. **Create README.txt**:
```
FTA Tariff Processing System
=============================

Quick Start:
1. Double-click SETUP_AND_RUN.bat (Windows) or ./setup_and_run.sh (Linux/Mac)
2. Wait for browser to open
3. Upload your XML files
4. Click "Run Processing Pipeline"
5. Download results

Requirements:
- Python 3.8 or higher
- Internet connection (first run only, for dependencies)

Folder Structure:
- input XML/     : Place your XML files here
- output_generated/ : Processed CSV files will appear here
- HS_IMP_v6.3.xlsm : Configuration file (edit if needed)

Support:
- See PORTABILITY_GUIDE.md for advanced options
- See README_IMPLEMENTATION.md for technical details
```

4. **Zip the package**:
```bash
zip -r FTA_Tariff_Processor_v2.0.zip FTA_Tariff_Processor_Portable/
```

---

## 🔒 Security Considerations

When distributing:

1. **Excel Macros**: The Excel file has macros disabled by design in Python (we read data only)
2. **Credentials**: Never hardcode API keys or passwords
3. **Data Privacy**: XML files may contain sensitive tariff data
4. **Virus Scanning**: PyInstaller executables may trigger false positives in antivirus software

---

## 🐛 Troubleshooting Portable Versions

### Common Issues:

1. **"Module not found" errors**:
   - Solution: Add to PyInstaller `--hidden-import` flag
   
2. **Excel file not found**:
   - Solution: Use relative paths with `Path(__file__).parent`
   
3. **Streamlit not starting**:
   - Solution: Add `--server.headless=true` to Streamlit command
   
4. **Large executable size**:
   - Solution: Use `--exclude-module` for unused dependencies
   - Alternative: Use embedded Python distribution instead

---

## ✅ Recommended Production Setup

### For Your Use Case:

**Best Approach**: **Embedded Python Distribution**

```
FTA_Tariff_Processor/
├── python/                          # Embedded Python 3.9
│   ├── python.exe
│   ├── Lib/
│   └── ...
├── src/                             # Application code
│   ├── config.py
│   ├── ingest.py
│   ├── process.py
│   ├── export.py
│   └── validation.py
├── app.py                           # Main application
├── HS_IMP_v6.3.xlsm                # Config file
├── requirements.txt                 # Dependencies
├── RUN_TARIFF_PROCESSOR.bat        # Launcher
├── input XML/                       # Input folder
├── output_generated/               # Output folder
├── README.txt                       # User guide
└── PORTABILITY_GUIDE.md            # This file
```

**Advantages**:
- ✅ No Python installation required
- ✅ Works offline after first setup
- ✅ Easy to update (replace files)
- ✅ Can be run from USB drive
- ✅ Single folder - easy to distribute

**Size**: ~100-150 MB (Python + dependencies)

---

## 📞 Support

For portability issues:
1. Check Python version: `python --version` (need 3.8+)
2. Verify dependencies: `pip list`
3. Test with sample data first
4. Check logs in terminal/command prompt

---

## 🎯 Summary

| Method | Portability | Ease of Use | Size | Offline | Recommended For |
|--------|-------------|-------------|------|---------|-----------------|
| **PyInstaller** | ⭐⭐⭐ | ⭐⭐⭐⭐ | Large | ✅ | Single-file distribution |
| **Docker** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Medium | ❌ | Server deployment |
| **Embedded Python** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Medium | ✅ | **End-user distribution** ⭐ |
| **Python Script** | ⭐⭐ | ⭐⭐⭐ | Small | ❌ | Development/Testing |

**Recommendation**: Use **Embedded Python Distribution** for easiest end-user experience.
