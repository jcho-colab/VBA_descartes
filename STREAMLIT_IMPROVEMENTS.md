# Streamlit UI Guide

## Overview

The FTA Tariff Rates Processor uses a modern Streamlit web interface for processing tariff data from XML files.

## Getting Started

### 1. Start the Application
```bash
streamlit run app.py
```

### 2. Select Country
- Use the dropdown in the sidebar to select a country
- Leave blank to use the default country from configuration
- Available countries: AU, BR, CA, EU, MX, NZ, RU, US, VN

### 3. Load Configuration
- Click "🔄 Load Configuration" button
- Configuration is loaded from `Configuration_files/` directory
- Success message shows country and year

### 4. Adjust Settings (Optional)
After loading configuration, you can adjust:
- **Year**: Processing year (default: 2026)
- **Min Chapter**: Minimum HS chapter to include (default: 25)
- **Max CSV Rows**: Maximum rows per output file (default: 30,000)

### 5. Upload XML Files
Upload your XML files in three categories:
- **DTR Files** (Required): Duty rate files matching pattern `*DTR*.xml`
- **NOM Files** (Required): Nomenclature files matching pattern `*NOM*.xml`
- **TXT Files** (Optional): Text/notes files matching pattern `*TXT*.xml`

The system automatically filters files by pattern and warns about mismatched files.

### 6. Configure Output
- **Skip Validation**: Option to bypass validation checks (not recommended)
- **Output Directory**: Where CSV files will be saved
  - Use the 📂 button to browse for a folder
  - Or type/paste the path directly

### 7. Run Processing
Click "🚀 Run Processing Pipeline" to start.

### 8. Reset (If Needed)
Click "🔄 Reset" to clear all settings and start over.

---

## Validation Behavior

### New Country Groups (BLOCKING)

If XML files contain country groups not in the configuration:

1. **Processing stops** with an error message
2. **New country groups are listed** 
3. **Instructions are provided** for updating the config

**To fix:**
1. Open `Configuration_files/{country}_config.json`
2. Add the new country group to `rate_types` array
3. Set `Comment` to `"keep"` or `"remove"`
4. Save, reload configuration, and re-run

### New UOMs (NON-BLOCKING)

If XML files contain UOMs not in the configuration:
- Processing continues
- Original XML values are used (no SAP mapping)
- Informational message is shown

---

## Configuration Files

### Location
All configuration is in `Configuration_files/` directory.

### Global Settings
`global_settings.json`:
```json
{
  "default_country": "NZ",
  "year": "2026",
  "min_chapter": 25,
  "max_csv": 30000
}
```

### Country Configuration
`{country}_config.json` (e.g., `nz_config.json`):
```json
{
  "rate_types": [
    {
      "Descartes CG": "_DNZ1 B001",
      "Comment": "keep",
      "Description": "General Rate"
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

### Comment Values
- `"keep"` - Include in processing
- `"remove"` - Exclude from processing
- Other values - Include in processing

---

## Output Types

| Country | Output Types |
|---------|--------------|
| All | ZD14 |
| Canada (CA) | ZD14, CAPDR, ZZDE |
| Mexico (MX) | ZD14, MX6Digits |
| United States (US) | ZD14, ZZDF |

---

## Troubleshooting

### "New Country Groups Detected"
See "Handling New Country Groups" in README_IMPLEMENTATION.md

### "No DTR/NOM files found"
Ensure filenames contain "DTR" or "NOM" respectively

### "Configuration directory not found"
Ensure `Configuration_files/` directory exists with JSON files

### Files ignored during upload
Check that filenames match expected patterns (*DTR*.xml, *NOM*.xml, *TXT*.xml)

---

## Tips

1. **Check file counts** after upload to ensure correct files were matched
2. **Review validation messages** before processing
3. **Use Reset button** if you need to start fresh
4. **Adjust Max CSV Rows** based on your system's memory capacity
