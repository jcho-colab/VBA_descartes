# Export HS Processing Guide

## Overview

This application now supports **two distinct workflows**:

1. **Import Tariffs Processing** (Original) - Processes DTR, NOM, and TXT files to generate tariff import data
2. **Export HS Processing** (New) - Processes NOM and TXT files to generate export HS code data

## Comparison of Workflows

### Import Tariffs (Original - "optional files" VBA)

**Purpose:** Process import tariff rates and duties from customs authorities

**Input Files:**
- **DTR** (Duty Rate) - Required
- **NOM** (Nomenclature) - Required
- **TXT** (Text) - Optional

**Processing Steps:**
1. Import and validate DTR files
2. Import and validate NOM files
3. Import TXT files (optional)
4. Filter by country groups and rate types
5. Apply complex business rules
6. Generate multiple output formats

**Output Formats:**
- **ZD14** - Primary import tariff format (CSV)
- **CAPDR** - Canada-specific format (CSV)
- **MX6Digits** - Mexico 6-digit format (CSV)
- **ZZDE** - Canada additional format (CSV)
- **ZZDF** - US format (CSV)

**File Format:** CSV (semicolon-delimited, UTF-8 with BOM)
**File Splitting:** Yes (default 30,000 rows per file)

**Configuration:** Complex
- Country groups (active/inactive)
- Duty rate types
- UOM mappings
- Rate validation rules

---

### Export HS (New - "CA_EXP" VBA)

**Purpose:** Process export HS codes and descriptions for customs declarations

**Input Files:**
- **NOM** (Nomenclature) - Required
- **TXT** (Text) - Optional (not used for US)

**Processing Steps:**
1. Import NOM files
2. Filter by chapter (remove unwanted chapters)
3. Process HS codes (remove double leading zeros)
4. Flag HS codes (active/invalid/duplicate)
5. Build hierarchical descriptions
6. Import TXT files (optional)
7. Generate export HS output

**Output Format:**
- **Export HS** (ExpHSCA, ExpHSUS, etc.) - Single Excel file

**File Format:** XLSX (Excel workbook)
**File Splitting:** No (single file output)

**Configuration:** Simple
- Country
- Year
- Minimum chapter

**Output Columns:**
- HS_Code
- Level
- Description (hierarchical)
- Official_Description
- Valid_From
- Valid_To
- Alt_Unit_1, Alt_Unit_2, Alt_Unit_3
- Text_Reference
- Country
- Year

---

## When to Use Each Workflow

### Use Import Tariffs When:
- You need to process customs duty rates and tariffs
- You have DTR (Duty Rate) files from customs authorities
- You need country group filtering
- You need multiple output formats (ZD14, CAPDR, etc.)
- You're importing goods and need tariff classification

### Use Export HS When:
- You need export HS codes and descriptions
- You only have NOM (and optionally TXT) files
- You don't have DTR files
- You need a simple Excel output
- You're exporting goods and need HS code reference data

---

## File Naming Conventions

### Import Tariffs XML Files:
- DTR: `HS{CountryCode}_IMP_EN_DTR*.xml`
- NOM: `HS{CountryCode}_IMP_EN_NOM*.xml`
- TXT: `HS{CountryCode}_IMP_EN_TXT*.xml`

Examples:
- `HSCA_IMP_EN_DTR_I_00007001001.xml`
- `HSNZ_IMP_EN_NOM_I_00007001001.xml`

### Export HS XML Files:
- NOM: `HS{CountryCode}_EXP_EN_NOM*.xml`
- TXT: `HS{CountryCode}_EXP_EN_TXT*.xml`

Examples:
- `HSCA_EXP_EN_NOM_I_00007001001.xml`
- `HSUS_EXP_EN_NOM_I_00007001001.xml`

---

## Technical Implementation Notes

### Shared Components (Reused for Both Workflows):
- `src/ingest.py` - XML parsing for both DTR and NOM files
- `src/config.py` - Configuration loading
- `src/process.py` - Core processing functions:
  - `cleanse_hs()` - Remove double leading zeros
  - `filter_by_chapter()` - Chapter filtering
  - `flag_hs()` - HS code flagging
  - `build_descriptions()` - Hierarchical description building

### Import-Specific Components:
- `src/export.py` - Functions:
  - `generate_zd14()`, `generate_capdr()`, etc.
  - `export_csv_split()` - CSV export with splitting
- Complex validation in `src/validation.py`

### Export-Specific Components:
- `src/export_hs.py` - New module:
  - `generate_export_hs()` - Export HS generation
- `src/export.py` - New function:
  - `export_xlsx()` - XLSX export (no splitting)

---

## User Interface

The Streamlit application has **three tabs**:

1. **🚀 Import Tariffs** - Original workflow
   - Upload DTR, NOM, TXT files
   - Configure output types (ZD14, CAPDR, etc.)
   - Get CSV files

2. **📤 Export HS** - New workflow
   - Upload NOM, TXT files
   - Simpler interface
   - Get single XLSX file

3. **ℹ️ Reference Info** - Documentation
   - Duty rate type definitions
   - Configuration reference

---

## Migration from VBA

### Original VBA (HS_IMP_v6.3.xlsm) → Import Tariffs Tab
- All functionality preserved
- Multi-step process with validation
- Country group filtering
- Multiple output formats

### CA_EXP VBA (HS_EXP_v1.xlsm) → Export HS Tab
- Simplified workflow
- NOM/TXT only
- Single XLSX output
- Hierarchical descriptions

---

## Example Usage

### Import Tariffs Workflow:
1. Select country configuration (e.g., CA for Canada)
2. Click "Load Configuration"
3. Upload DTR, NOM, and TXT XML files
4. Select output types (ZD14, CAPDR, ZZDE)
5. Click "Run Processing Pipeline"
6. Download ZIP with CSV files

### Export HS Workflow:
1. Ensure configuration is loaded (uses same country config)
2. Switch to "Export HS" tab
3. Upload NOM XML file (required)
4. Upload TXT XML file (optional)
5. Click "Run Export HS Pipeline"
6. Download XLSX file

---

## Troubleshooting

### Import Tariffs Issues:
- **Missing DTR rates**: Check validation messages
- **New country groups**: Update configuration JSON
- **Large files**: Files auto-split at 30,000 rows

### Export HS Issues:
- **Empty output**: Verify NOM files contain valid HS codes
- **Missing descriptions**: Check parent_id references in NOM
- **Chapter filtering**: Adjust min_chapter in configuration

---

## Configuration Files

Both workflows use the same configuration files from `Configuration_files/`:
- `global_settings.json` - Default settings
- `{country}_config.json` - Country-specific settings

Export HS uses a subset of the configuration:
- Country
- Year
- Min chapter
- Chapter list

Import Tariffs uses full configuration:
- All of the above plus:
- Rate types
- Country groups
- UOM mappings
- Max CSV rows

---

## Performance Notes

### Import Tariffs:
- Processing time: 2-10 minutes (depending on file size)
- Memory usage: High (multiple dataframes)
- Output size: Multiple files, can be large

### Export HS:
- Processing time: 30 seconds - 2 minutes
- Memory usage: Moderate (single dataframe)
- Output size: Single file, typically < 5MB

---

## Support

For issues or questions:
1. Check error messages in the UI
2. Review this guide
3. Examine log files
4. Verify XML file formats match expected patterns
