#!/usr/bin/env python3
"""
Create a portable distribution package of the FTA Tariff Processor.
This script creates a ZIP file with all necessary files for distribution.
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def create_portable_package():
    """Create a portable distribution package."""
    
    print("="*80)
    print("FTA Tariff Processor - Portable Package Creator")
    print("="*80)
    
    # Define package name with version and date
    version = "v2.0"
    date_str = datetime.now().strftime("%Y%m%d")
    package_name = f"FTA_Tariff_Processor_{version}_{date_str}"
    package_dir = Path(package_name)
    
    # Create package directory
    if package_dir.exists():
        print(f"\n[INFO] Removing existing package: {package_name}")
        shutil.rmtree(package_dir)
    
    print(f"\n[INFO] Creating package directory: {package_name}")
    package_dir.mkdir(exist_ok=True)
    
    # Create subdirectories
    (package_dir / "input XML").mkdir(exist_ok=True)
    (package_dir / "output_generated").mkdir(exist_ok=True)
    
    # Copy source files
    print("\n[INFO] Copying source files...")
    
    files_to_copy = [
        ("app.py", "Main Streamlit application"),
        ("requirements.txt", "Python dependencies"),
        ("HS_IMP_v6.3.xlsm", "Configuration Excel file"),
        ("RUN_TARIFF_PROCESSOR.bat", "Windows launcher"),
        ("run_tariff_processor.sh", "Linux/Mac launcher"),
        ("README_IMPLEMENTATION.md", "Implementation documentation"),
        ("PORTABILITY_GUIDE.md", "Portability guide"),
        ("test_run.py", "Test script"),
        ("verify.py", "Verification script"),
    ]
    
    for file, description in files_to_copy:
        if Path(file).exists():
            shutil.copy(file, package_dir / file)
            print(f"  ✓ {file:30s} - {description}")
        else:
            print(f"  ⚠ {file:30s} - NOT FOUND")
    
    # Copy src directory
    if Path("src").exists():
        print("\n[INFO] Copying src/ directory...")
        shutil.copytree("src", package_dir / "src")
        print("  ✓ src/ directory copied")
    
    # Copy sample input files (optional)
    if Path("input XML").exists():
        sample_files = list(Path("input XML").glob("*.xml"))[:3]  # Copy first 3 as samples
        if sample_files:
            print("\n[INFO] Copying sample XML files...")
            for xml_file in sample_files:
                shutil.copy(xml_file, package_dir / "input XML" / xml_file.name)
                print(f"  ✓ {xml_file.name}")
    
    # Create README.txt for package
    print("\n[INFO] Creating README.txt...")
    readme_content = f"""
FTA Tariff Processing System - Portable Package
================================================

Version: {version}
Package Date: {date_str}

QUICK START
-----------

Windows Users:
  1. Double-click "RUN_TARIFF_PROCESSOR.bat"
  2. Wait for browser to open automatically
  3. Follow on-screen instructions

Linux/Mac Users:
  1. Open terminal in this folder
  2. Run: chmod +x run_tariff_processor.sh
  3. Run: ./run_tariff_processor.sh
  4. Wait for browser to open
  5. Follow on-screen instructions

FIRST-TIME SETUP
-----------------
The launcher script will automatically:
- Check if Python 3.8+ is installed
- Install required dependencies (one-time)
- Create necessary folders
- Launch the application

REQUIREMENTS
------------
- Python 3.8 or higher (https://www.python.org/downloads/)
- Internet connection (first run only, for installing dependencies)
- Modern web browser (Chrome, Firefox, Edge, Safari)

FOLDER STRUCTURE
----------------
- input XML/          : Place your DTR, NOM, TXT XML files here
- output_generated/   : Processed CSV files will be saved here
- src/                : Application source code (do not modify)
- HS_IMP_v6.3.xlsm    : Configuration file (can be customized)

USAGE
-----
1. Place configuration Excel file (HS_IMP_v6.3.xlsm) in this folder
2. Run the launcher script for your operating system
3. In the web interface:
   - Load configuration (sidebar)
   - Upload XML files (DTR, NOM, TXT)
   - Configure processing options
   - Click "Run Processing Pipeline"
   - Download generated CSV files

FEATURES
--------
✓ XML file parsing (DTR, NOM, TXT formats)
✓ Data cleansing and validation
✓ HS code flagging (active/invalid/duplicate)
✓ Hierarchical description building
✓ Multiple output formats (ZD14, CAPDR, MX6Digits, ZZDE, ZZDF)
✓ CSV export with automatic file splitting
✓ Country-specific processing logic

SUPPORTED COUNTRIES
-------------------
- NZ (New Zealand)
- CA (Canada) - includes CAPDR, ZZDE
- US (United States) - includes ZZDF
- MX (Mexico) - includes MX6Digits
- BR (Brazil)
- EU (European Union)

OUTPUT FILES
------------
Generated CSV files use:
- Semicolon (;) delimiter
- UTF-8 with BOM encoding
- YYYYMMDD date format
- Automatic splitting for large files

DOCUMENTATION
-------------
- README_IMPLEMENTATION.md : Technical implementation details
- PORTABILITY_GUIDE.md     : Guide for creating executables
- For support, check the documentation files

TROUBLESHOOTING
---------------
1. "Python not found"
   → Install Python 3.8+ from https://www.python.org

2. "Module not found" errors
   → Run launcher script again (it will install dependencies)

3. Browser doesn't open
   → Manually open: http://localhost:8501

4. "Config file not found"
   → Ensure HS_IMP_v6.3.xlsm is in the package folder

5. XML files not processing
   → Check XML files are valid DTR/NOM/TXT format
   → Ensure file names follow naming convention

TECHNICAL SUPPORT
-----------------
For technical issues:
1. Check Python version: python --version (need 3.8+)
2. Verify dependencies: pip list
3. Review error messages in terminal
4. Check log files if created

LICENSE & COPYRIGHT
-------------------
Internal tool for FTA tariff processing.
All rights reserved.

CHANGELOG
---------
{version} ({date_str}):
- Initial portable distribution
- Full hierarchical descriptions
- Complete VBA parity
- All output types implemented
- Validation system included

================================================
Generated by: create_portable_package.py
Package: {package_name}
================================================
"""
    
    with open(package_dir / "README.txt", "w") as f:
        f.write(readme_content.strip())
    print("  ✓ README.txt created")
    
    # Create .gitignore
    print("\n[INFO] Creating .gitignore...")
    gitignore_content = """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/

# Output
output_generated/*.csv
!output_generated/.gitkeep

# Input (keep structure, ignore files)
input XML/*.xml

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
"""
    with open(package_dir / ".gitignore", "w") as f:
        f.write(gitignore_content.strip())
    print("  ✓ .gitignore created")
    
    # Create .gitkeep files
    (package_dir / "input XML" / ".gitkeep").touch()
    (package_dir / "output_generated" / ".gitkeep").touch()
    
    # Create ZIP file
    print(f"\n[INFO] Creating ZIP archive...")
    zip_filename = f"{package_name}.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                arc_name = file_path.relative_to(package_dir.parent)
                zipf.write(file_path, arc_name)
                
    zip_size_mb = Path(zip_filename).stat().st_size / 1024 / 1024
    print(f"  ✓ {zip_filename} created ({zip_size_mb:.2f} MB)")
    
    # Summary
    print("\n" + "="*80)
    print("✅ PACKAGE CREATION COMPLETE")
    print("="*80)
    print(f"\nPackage folder: {package_dir}/")
    print(f"ZIP archive:    {zip_filename} ({zip_size_mb:.2f} MB)")
    print(f"\nDistribution ready!")
    print("\nTo distribute:")
    print(f"  1. Share {zip_filename}")
    print("  2. Users extract and run launcher script")
    print("  3. Application runs in browser")
    print("\n" + "="*80)

if __name__ == "__main__":
    try:
        create_portable_package()
    except Exception as e:
        print(f"\n❌ Error creating package: {e}")
        import traceback
        traceback.print_exc()
