# Export HS Fixes - Date and UOM Issues

## Issues Identified

### Issue 1: Start Date showing "200001" - This is Correct

**Root Cause:**
- The VBA Power Query M code for **Canada (CA)** does NOT use the XML's `valid_from` date
- Instead, it constructs the date as: `configYear & "01"` (e.g., "2000" + "01" = "200001")
- The Excel configuration has Year = 2000, which produces "200001" as intended
- The Python code was incorrectly using the XML dates instead of config year

**VBA M Code (CA):**
```m
configYear = Excel.CurrentWorkbook(){[Name="Year"]}[Content]{0}[Column1],
addStart = Table.AddColumn(renameUOM, "Start date", each Number.ToText(configYear) & "01", type text),
addEnd = Table.AddColumn(addStart, "End date", each "999912", type text),
```

**Fix Applied:**
- For **CA**: Start date = `{config.year}01`, End date = `"999912"` (hardcoded)
- For **US**: Start date and End date use actual XML dates (`valid_from`, `valid_to`) converted to YYYYMM format
- **Export HS tab (tab 2) always uses year "2000"** (forced in `app.py`), producing "200001" for both CA and US
- Import Tariffs tab (tab 1) uses the global default year "2026" from `global_settings.json`

---

### Issue 2: UOM showing "N/A" instead of actual values

**Root Cause:**
- The VBA Power Query M code replaces `null` values with `"NMB"` (Number), NOT `"N/A"`
- When `alternate_unit_1` has a value (like "NMB", "KGM", "DZN"), it keeps that value
- When `alternate_unit_1` is empty/null, it defaults to `"NMB"`
- The Python code was incorrectly using `"N/A"` as the default

**VBA M Code:**
```m
fillUOM = Table.ReplaceValue(selectCols, null, "NMB", Replacer.ReplaceValue, {"alternate_unit_1"}),
```

**Fix Applied:**
- Changed default UOM from `"N/A"` to `"NMB"` to match VBA behavior
- Added logging to track how many empty UOM values are being defaulted

---

## Additional Differences Between CA and US

### Canada (CA):
- **Level ID**: 40 (8-digit HS codes)
- **Start Date**: Constructed from config year + "01" (e.g., "200001" when Export HS tab uses year 2000)
- **End Date**: Always "999912" (hardcoded)
- **Dates Source**: Ignores XML dates, uses config year
- **Export HS Year**: Always 2000 (forced in `app.py` for tab 2)

### United States (US):
- **Level ID**: 50 (8-digit HS codes)
- **valid_from**: From XML `valid_from` (kept as date type, not converted)
- **valid_to**: From XML `valid_to` (kept as date type, not converted)
- **Dates Source**: Uses actual XML dates as-is
- **Output Format**: Completely different from CA
  - Columns: valid_from, valid_to, hs, UOM, full_description
  - No "Start date", "End date", or "HS8_*" columns
  - No French description column

---

## Code Changes Made

### File: `app.py`

1. **Added year override for Export HS tab** (lines ~248-250):
   - Creates a copy of the config with year forced to "2000"
   - Uses `dataclasses.replace()` to create a modified config
   - Ensures Export HS processing always uses year 2000 regardless of country
   - Only affects tab 2 (Export HS), tab 1 (Import Tariffs) uses the configured year

### File: `src/config.py`

1. **Added country-specific year override capability** (lines 97-100):
   - Config loader checks for optional "year" field in country-specific config files
   - If present, overrides the global year setting
   - Provides flexibility for future country-specific year needs
   - Currently not used by any country config

### File: `src/export_hs.py`

1. **Completely different output formats for CA vs US** (lines 74-104):
   - **CA format**: 6 columns (Start date, End date, HS8_Code, HS8_Unit_of_Measure_Code, HS8_Edesc, HS8_Fdesc)
   - **US format**: 5 columns (valid_from, valid_to, hs, UOM, full_description)
   - CA uses config year for dates: `f"{config.year}01"` for start, `"999912"` for end
   - US uses XML dates as-is (kept as date type, not converted to YYYYMM)

2. **Updated UOM default for CA** (line 84):
   - Changed from `'N/A'` to `'NMB'`
   - Applied directly in DataFrame creation using `.fillna('NMB')`
   - US keeps UOM as-is from XML (no default)

3. **Updated level filtering** (lines 56-61):
   - CA uses level_id = 40 (8-digit codes)
   - US uses level_id = 50 (8-digit codes)
   - Dynamically selects based on country

4. **Added logging**:
   - Logs which format is being used (CA vs US)
   - Logs which dates are being used for CA
   - Helps with debugging and verification

5. **Updated docstring**:
   - Documents CA vs US format differences
   - Explains date construction logic for each country
   - Lists exact columns for each output format

---

## Configuration Note

The year value is controlled differently for each tab:

**Tab 1 (Import Tariffs):**
- Uses the global default year from `Configuration_files/global_settings.json` (currently "2026")
- Can be overridden by the user in the UI

**Tab 2 (Export HS):**
- **Always uses year 2000** regardless of country selection (CA or US)
- This is hardcoded in `app.py` (line ~248) to match the legacy VBA Excel implementation
- Produces Start date = "200001" for both CA and US
- This is the expected behavior for Export HS processing

---

## Verification Checklist

When testing the fixes, verify:

### Canada (CA):
- [ ] **Columns**: Start date, End date, HS8_Code, HS8_Unit_of_Measure_Code, HS8_Edesc, HS8_Fdesc
- [ ] **Start Date**: Should be `{Year}01` (e.g., "200001" for year 2000)
- [ ] **End Date**: Should always be "999912"
- [ ] **UOM defaults**: Empty UOM should default to "NMB"
- [ ] **Level**: Should filter level_id = 40

### United States (US):
- [ ] **Columns**: valid_from, valid_to, hs, UOM, full_description
- [ ] **Dates**: Should be date types from XML (not YYYYMM text format)
- [ ] **UOM values**: Should show actual values from XML
- [ ] **Level**: Should filter level_id = 50

---

## Example Output

### Canada (CA) - Expected Format (Year = 2000 in Export HS tab):
```
Start date | End date | HS8_Code | HS8_Unit_of_Measure_Code | HS8_Edesc          | HS8_Fdesc
200001     | 999912   | 01012100 | NMB                      | Horses; Pure-bred... |
200001     | 999912   | 01012910 | NMB                      | For slaughter      |
200001     | 999912   | 02011000 | KGM                      | Carcasses and...   |
```

### United States (US) - Expected Format (Completely Different):
```
valid_from | valid_to   | hs       | UOM | full_description
2017-01-01 | 9999-12-31 | 01012100 | NMB | Horses; Pure-bred breeding animals
2017-01-01 | 9999-12-31 | 01012910 | NMB | Horses; Live; Other than pure-bred breeding animals; For slaughter
2017-01-01 | 9999-12-31 | 02011000 | KGM | Meat of bovine animals; Fresh or chilled; Carcasses and half-carcasses
```

**Note**: US format has:
- 5 columns (not 6)
- Date types (not YYYYMM text)
- Different column names (hs, UOM, full_description instead of HS8_Code, HS8_Unit_of_Measure_Code, HS8_Edesc)
- No HS8_Fdesc column

---

## Related Files

- `app.py` - Main Streamlit app with Export HS tab forcing year=2000 (UPDATED)
- `src/export_hs.py` - Main export HS generation logic (UPDATED)
- `src/config.py` - Configuration loader with optional country-specific year override (UPDATED)
- `Configuration_files/global_settings.json` - Contains global default year value (2026)
- `CA_EXP/Macro VBA/HS_EXP_v1.xlsm` - Original VBA implementation
- `EXPORT_HS_GUIDE.md` - General export HS documentation
