# Quick Start Guide

## Two Workflows in One Application

This application handles **both Import and Export tariff processing** in separate tabs.

---

## 🚀 Import Tariffs (Original Workflow)

**When to use:** Processing customs duty rates and import tariffs

### Files Required:
- ✅ DTR (Duty Rate) - **Required**
- ✅ NOM (Nomenclature) - **Required**
- ⭕ TXT (Text) - Optional

### File Pattern:
```
HS{CountryCode}_IMP_EN_DTR*.xml
HS{CountryCode}_IMP_EN_NOM*.xml
HS{CountryCode}_IMP_EN_TXT*.xml
```

### Steps:
1. Select country (e.g., CA, US, NZ)
2. Click "Load Configuration"
3. Go to "Import Tariffs" tab
4. Upload DTR, NOM, and optionally TXT files
5. Select output formats (ZD14, CAPDR, etc.)
6. Click "Run Processing Pipeline"
7. Download ZIP with CSV files

### Output:
- **ZD14** - Primary format (always generated)
- **CAPDR** - Canada-specific (if CA selected)
- **ZZDE** - Canada additional (if CA selected)
- **MX6Digits** - Mexico format (if MX selected)
- **ZZDF** - US format (if US selected)

**Format:** Multiple CSV files (semicolon-delimited)
**Size:** Auto-splits at 30,000 rows

---

## 📤 Export HS (New Workflow)

**When to use:** Processing export HS codes and descriptions for CA and US only
**Required** Make sure the tab 'Export HS' is clickable only if the country group is CA or US.

### Files Required:
- ✅ NOM (Nomenclature) - **Required**
- ⭕ TXT (Text) - Optional (not needed for US)

### File Pattern:
```
HS{CountryCode}_EXP_EN_NOM*.xml
HS{CountryCode}_EXP_EN_TXT*.xml
```

### Steps:
1. Ensure configuration is loaded (same as Import)
2. Go to "Export HS" tab
3. Upload NOM file
4. Optionally upload TXT file
5. Click "Run Export HS Pipeline"
6. Download XLSX file

### Output:
- **ExpHS{Country}** - Single Excel file with export HS codes

**Format:** XLSX (Excel workbook)
**Size:** Single file (no splitting)

---

## Configuration

Both workflows use the same configuration:

### First-Time Setup:
1. Country configuration files are in `Configuration_files/`
2. Select country from dropdown
3. Click "Load Configuration"

### Settings:
- **Year:** Processing year (default: 2000)
- **Min Chapter:** Minimum HS chapter to include (default: 25)
- **Output Directory:** Where files are saved

### Editing Settings:
- Use the sidebar "Edit Settings" section
- Changes apply immediately
- Affects both Import and Export workflows

---

## Common Issues & Solutions

### "Please upload DTR and NOM files"
- **Cause:** Missing required files in Import Tariffs
- **Solution:** Make sure to upload both DTR and NOM files

### "New Country Groups Detected"
- **Cause:** XML contains country groups not in configuration
- **Solution:** Add the displayed groups to your country config JSON file

### "DataFrame is empty"
- **Cause:** No valid HS codes after filtering
- **Solution:** Check your min_chapter setting or XML file content

### "Module not found"
- **Cause:** Missing dependencies
- **Solution:** Run `pip install -r requirements.txt`

---

## File Locations

### Input:
Upload via web interface (temporary storage)

### Output:
Default: `output_generated/`
Custom: Specify in "Output Directory" field

### Configuration:
`Configuration_files/{country}_config.json`

### Logs:
Console output (visible in terminal running Streamlit)

---

## Tips

### Import Tariffs:
- ✅ Always validate before processing
- ✅ Check country group configurations
- ✅ Use skip validation only if you're certain
- ✅ Preview output before downloading

### Export HS:
- ✅ NOM files are sufficient for basic export
- ✅ TXT files add reference information
- ✅ US doesn't need TXT files
- ✅ Output includes hierarchical descriptions

### Both:
- ✅ Use consistent file naming
- ✅ Check year in configuration
- ✅ Verify chapter filtering
- ✅ Monitor progress bar for issues

