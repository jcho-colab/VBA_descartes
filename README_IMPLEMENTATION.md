# FTA Tariff Rates Processing System

## Overview
Python-based migration of the Excel/VBA macro system for processing FTA (Free Trade Agreement) tariff rates from Descartes XML files.

## Features Implemented

### ✅ Core Functionality
- **XML Parsing**: Ingests DTR (Duty Rate), NOM (Nomenclature), and TXT (Text) XML files
- **Data Cleansing**: Removes leading zeros, filters invalid chapters
- **Flagging System**: Marks records as active/invalid/duplicate
- **Description Building**: Creates hierarchical nomenclature descriptions
- **Multiple Output Types**: ZD14, CAPDR, MX6Digits, ZZDE, ZZDF

### ✅ Validation
- **Rate Validation**: Checks all DTR records have rate text or regulation
- **Config Validation**: Warns about unmapped country groups and UOMs
- **Data Integrity**: Ensures data quality before processing

### ✅ Export Features
- **CSV Generation**: Semicolon-delimited with UTF-8 BOM encoding
- **File Splitting**: Automatically splits large files (default: 1M rows)
- **Version Management**: Auto-increments version numbers
- **Country-Specific Logic**: 
  - US: T → TO replacement in UOM
  - Brazil: Clears rate amount field
  - Canada: CAPDR and ZZDE formats
  - Mexico: MX6Digits format

### ✅ User Interface
- **Streamlit Web App**: Modern, responsive interface
- **Progress Tracking**: Real-time progress bars and status updates
- **Error Handling**: Comprehensive error messages and recovery
- **Configuration Management**: Flexible country and year selection
- **Output Preview**: View generated data before download

## Directory Structure

```
/app/
├── src/
│   ├── config.py           # Configuration loader
│   ├── ingest.py           # XML parsing
│   ├── process.py          # Data processing and cleansing
│   ├── export.py           # CSV generation
│   └── validation.py       # Validation functions
├── app.py                  # Streamlit web interface
├── verify.py               # Verification script
├── requirements.txt        # Python dependencies
├── HS_IMP_v6.3.xlsm       # Configuration Excel file
├── input XML/             # Input XML files
├── output CSV/            # VBA reference output
└── output_generated/      # Python generated output
```

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup
```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

### Web Interface (Recommended)
```bash
# Start Streamlit app
streamlit run app.py

# Open browser to http://localhost:8501
```

### Command Line
```python
from src.config import ConfigLoader
from src.ingest import parse_xml_to_df
from src.process import *
from src.export import *

# Load configuration
config = ConfigLoader("HS_IMP_v6.3.xlsm").load()

# Process files
dtr_df = parse_xml_to_df(dtr_files, "DTR")
nom_df = parse_xml_to_df(nom_files, "NOM")

# Clean and process
dtr_df = cleanse_hs(dtr_df, 'hs')
dtr_df = filter_by_chapter(dtr_df, config)
dtr_df = flag_hs(dtr_df, config, "DTR")

nom_df = build_descriptions(nom_df)

# Generate output
zd14 = generate_zd14(dtr_df, nom_df, config)
export_csv_split(zd14, "output", f"{config.country} UPLOAD _ZD14")
```

## Verification

Compare Python output with VBA reference:
```bash
python verify.py
```

## Configuration

### Excel Configuration File
The system reads configuration from `HS_IMP_v6.3.xlsm`:

**Named Ranges (Menu tab):**
- `Country`: Country code (NZ, CA, US, MX, BR, EU)
- `Year`: Processing year (e.g., 2025)
- `MinChapter`: Minimum HS chapter (typically 25)
- `MaxCSV`: Maximum rows per CSV file (default: 1,000,000)
- `ZD14Date`: Reference date for ZD14 generation

**Tables (Config tab):**
- `{Country}RateType`: Country group mappings (Keep/Remove/3rd)
- `{Country}UOM`: Unit of measure mappings (Descartes → SAP)
- `{Country}CountryList`: Country list for EU multi-country export

### Environment Variables
None required - all configuration is in the Excel file.

## Output Formats

### ZD14 (All Countries)
Standard tariff format with:
- Country, HS Number, Validity dates
- English and Spanish descriptions
- Unit of measure
- Rate type, Base rate %, Rate amount
- Certificate of origin

### CAPDR (Canada)
Canada-specific tariff format (extends ZD14)

### MX6Digits (Mexico)
Mexico-specific 6-digit format (extends ZD14)

### ZZDE (Canada)
Additional Canada format (extends ZD14)

### ZZDF (United States)
US-specific format with T→TO replacements (extends ZD14)

## Improvements Over VBA

1. **Performance**: Pandas vectorized operations vs Excel row-by-row
2. **Scalability**: Handles 100k+ rows efficiently
3. **Error Handling**: Comprehensive validation and recovery
4. **User Interface**: Modern web UI vs Excel dialog boxes
5. **Maintainability**: Modular Python code vs VBA macros
6. **Portability**: Runs on any platform with Python
7. **Testing**: Automated verification against reference output

## Known Limitations

1. **Special Output Formats**: CAPDR, MX6Digits, ZZDE, ZZDF use ZD14 base (full format TBD)
2. **TXT Files**: Parsed but not currently used in output generation
3. **Complex Rates**: Full handling of compound and complex rates pending
4. **EU Multi-Country**: Multi-country export logic implemented but needs testing

## Testing

### Test Data
Sample files are provided in `/app/input XML/`:
- 17 DTR files (HSNZ_IMP_EN_DTR_I_*.xml)
- 3 NOM files (HSNZ_IMP_EN_NOM_I_*.xml)
- 1 TXT file (HSNZ_IMP_EN_TXT_I_*.xml)

### Expected Output
Reference output in `/app/output CSV/`:
- 6 CSV files (NZ UPLOAD _ZD14 V1-1.csv through V1-6.csv)

### Running Tests
```bash
# Process test data
streamlit run app.py

# Verify against reference
python verify.py
```

## Troubleshooting

### Issue: Configuration file not found
**Solution**: Update Excel path in sidebar or place file at `/app/HS_IMP_v6.3.xlsm`

### Issue: Missing rate text warnings
**Solution**: Check DTR XML files have rate descriptions or regulations. Can continue processing with warning.

### Issue: Unmapped UOM warnings
**Solution**: Add missing UOMs to {Country}UOM table in Config tab

### Issue: Output doesn't match VBA
**Solution**: 
1. Check chapter filtering (MinChapter setting)
2. Verify country group configuration
3. Review rate formatting precision
4. Run verify.py for detailed comparison

## Support

For issues or questions:
1. Check error logs in terminal/console
2. Review validation warnings in UI
3. Compare with VBA output using verify.py
4. Check configuration in Excel file

## Version History

### Version 2.0 (Current)
- ✅ Added validation module (rate and config validation)
- ✅ Implemented all output types (CAPDR, MX6Digits, ZZDE, ZZDF)
- ✅ Enhanced config loader with chapter list generation
- ✅ Improved error handling throughout
- ✅ Added file versioning
- ✅ Better rate formatting
- ✅ Country-specific logic (US, Brazil)
- ✅ Modern Streamlit UI with progress tracking
- ✅ Verification script for output comparison

### Version 1.0
- Basic ZD14 generation
- DTR/NOM XML parsing
- Data cleansing and flagging
- Simple Streamlit interface

## License

Internal tool for FTA tariff processing.
