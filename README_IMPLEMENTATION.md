# FTA Tariff Rates Processing System

## Overview
Python-based migration of the Excel/VBA macro system for processing FTA (Free Trade Agreement) tariff rates from Descartes XML files.

## Features Implemented

### Core Functionality
- **XML Parsing**: Ingests DTR (Duty Rate), NOM (Nomenclature), and TXT (Text) XML files
- **Data Cleansing**: Removes leading zeros, filters invalid chapters
- **Flagging System**: Marks records as active/invalid/duplicate
- **Description Building**: Creates hierarchical nomenclature descriptions
- **Multiple Output Types**: ZD14, CAPDR, MX6Digits, ZZDE, ZZDF

### Validation
- **Rate Validation**: Checks all DTR records have rate text or regulation
- **Country Group Validation**: Blocks processing if new country groups are detected (requires config update)
- **UOM Validation**: Warns about unmapped UOMs (non-blocking, uses original values)
- **Data Integrity**: Ensures data quality before processing

### Export Features
- **CSV Generation**: Semicolon-delimited with UTF-8 BOM encoding
- **File Splitting**: Automatically splits large files (default: 30,000 rows)
- **Version Management**: Auto-increments version numbers
- **Country-Specific Logic**: 
  - US: T → TO replacement in UOM
  - Brazil: Clears rate amount field
  - Canada: CAPDR and ZZDE formats
  - Mexico: MX6Digits format

### User Interface
- **Streamlit Web App**: Modern, responsive interface
- **Progress Tracking**: Real-time progress bars and status updates
- **Error Handling**: Comprehensive error messages and recovery
- **Configuration Management**: JSON-based configuration files
- **Output Preview**: View generated data before download
- **Reset Button**: Clear all settings and start over

## Directory Structure

```
/app/
├── Configuration_files/    # JSON configuration files
│   ├── global_settings.json
│   ├── au_config.json
│   ├── br_config.json
│   ├── ca_config.json
│   ├── eu_config.json
│   ├── mx_config.json
│   ├── nz_config.json
│   ├── ru_config.json
│   ├── us_config.json
│   └── vn_config.json
├── src/
│   ├── config.py           # Configuration loader (JSON-based)
│   ├── ingest.py           # XML parsing
│   ├── process.py          # Data processing and cleansing
│   ├── export.py           # CSV generation
│   └── validation.py       # Validation functions
├── app.py                  # Streamlit web interface
├── verify.py               # Verification script
└── requirements.txt        # Python dependencies
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

# Load configuration from JSON files
config = ConfigLoader("Configuration_files").load("NZ")

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

## Configuration

### JSON Configuration Files

Configuration is stored in the `Configuration_files/` directory as JSON files.

#### Global Settings (`global_settings.json`)
```json
{
  "default_country": "NZ",
  "year": "2026",
  "min_chapter": 25,
  "max_csv": 30000,
  "zd14_date": null
}
```

#### Country Configuration (`{country}_config.json`)
Each country has its own configuration file containing:

**Rate Types** - Defines which country groups to include/exclude:
```json
{
  "rate_types": [
    {
      "Descartes CG": "_DNZ1 B001",
      "Comment": "keep",
      "Description": "General Rate"
    },
    {
      "Descartes CG": "_DNZ10 B004",
      "Comment": "remove",
      "Description": "Singapore Rate"
    }
  ],
  "uom_mappings": [
    {
      "Descartes UOM": "DOZ",
      "SAP UOM": "DZ"
    }
  ]
}
```

**Comment Values:**
- `"keep"` - Include this country group in processing
- `"remove"` - Exclude this country group from processing
- Any other value (e.g., `"3rd"`) - Include in processing

### Adding a New Country

1. Create `Configuration_files/{country}_config.json`
2. Add rate_types and uom_mappings arrays
3. The country will automatically appear in the dropdown

## Handling New Country Groups

When processing XML files, the system validates that all country groups exist in the configuration. If new country groups are detected:

### What Happens
1. Processing is **blocked** with an error message
2. The new country group codes are displayed
3. Step-by-step instructions are shown

### How to Fix

1. **Identify the new country group** from the error message (e.g., `_DNZ99`)

2. **Open the country's config file**: `Configuration_files/{country}_config.json`

3. **Add the new country group** to the `rate_types` array:
   ```json
   {
     "Descartes CG": "_DNZ99 B004",
     "Comment": "keep",
     "Description": "New Trade Agreement Rate"
   }
   ```

4. **Set the Comment field:**
   - `"keep"` - To include this country group in output
   - `"remove"` - To exclude this country group from output

5. **Save the file**

6. **In the app:**
   - Click "Load Configuration" to reload
   - Re-upload your XML files
   - Run processing again

### Example

If you see this error:
```
🚫 New Country Groups Detected - Action Required

New country groups to add:
_DNZ27
_DNZ28
```

Add to `Configuration_files/nz_config.json`:
```json
{
  "rate_types": [
    // ... existing entries ...
    {
      "Descartes CG": "_DNZ27 B004",
      "Comment": "keep",
      "Description": "New Agreement 1"
    },
    {
      "Descartes CG": "_DNZ28 B004",
      "Comment": "keep", 
      "Description": "New Agreement 2"
    }
  ]
}
```

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

## Troubleshooting

### Issue: New Country Groups Detected
**Solution**: Add the new country groups to the configuration file. See "Handling New Country Groups" section above.

### Issue: Missing rate text warnings
**Solution**: Check DTR XML files have rate descriptions or regulations. Can continue processing with warning.

### Issue: Unmapped UOM warnings
**Solution**: UOMs not in config will use their original XML values. To add SAP mappings, edit the `uom_mappings` array in the country config file.

### Issue: Configuration directory not found
**Solution**: Ensure `Configuration_files/` directory exists with the required JSON files.

### Issue: Output doesn't match expected
**Solution**: 
1. Check chapter filtering (Min Chapter setting)
2. Verify country group configuration (keep vs remove)
3. Review rate formatting precision
4. Check year setting

## Version History

### Version 3.0 (Current)
- JSON-based configuration (removed Excel dependency)
- Blocking validation for new country groups
- Reset button to clear all settings
- Reduced UI padding for better space usage
- Folder browser button for output directory
- Default year: 2026, Max CSV: 30,000

### Version 2.0
- Added validation module (rate and config validation)
- Implemented all output types (CAPDR, MX6Digits, ZZDE, ZZDF)
- Enhanced config loader with chapter list generation
- Improved error handling throughout
- Added file versioning
- Better rate formatting
- Country-specific logic (US, Brazil)
- Modern Streamlit UI with progress tracking
- Verification script for output comparison

### Version 1.0
- Basic ZD14 generation
- DTR/NOM XML parsing
- Data cleansing and flagging
- Simple Streamlit interface

## License

Internal tool for FTA tariff processing.
