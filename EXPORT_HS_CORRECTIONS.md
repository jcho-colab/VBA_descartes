# Export HS Corrections

## Issue
The generated Export HS output was "very different" from the expected output in `CA_EXP/output XLSX/UPLOAD ExpHSCA V1 20260127.xlsx`.

## Root Cause Analysis

After analyzing the CA_EXP VBA code in detail, I found **key differences** between Import and Export workflows:

### 1. FlagHS Function Difference

**Import FlagHS (optional files/Macro VBA/mSubs.bas lines 307-458):**
- Sorts by `version_number` (for NOM) or `country_group` (for DTR) **FIRST**
- Then sorts by HS, version_date, valid_from, valid_to
- Groups flagging by the key (version_number/country_group)
- Flags first occurrence within each group

**Export FlagHS (CA_EXP/Macro VBA/mSubs.bas lines 254-352):**
- **NO version_number grouping**
- Sorts by HS, version_date, valid_from, valid_to only
- Flags globally per HS (not per group)
- First occurrence of any HS code -> active/invalid
- Subsequent occurrences -> duplicate

###2. Output Format

The VBA `QueryOutput` function (CA_EXP lines 425-447) refreshes a QueryTable that:
- Selects specific columns from the processed NOM table
- Filters for `hs_flag = '01-active'` only
- Sorts by HS code

The `ExportXLSX` function (CA_EXP lines 449-484) then:
- Copies the entire QueryTable range to Excel
- Saves as XLSX file

## Corrections Made

### 1. Updated `src/process.py::flag_hs()`

Added `is_export` parameter:

```python
def flag_hs(df: pd.DataFrame, config: AppConfig, doc_type: str, is_export: bool = False) -> pd.DataFrame:
    # ...
    if doc_type == "NOM":
        if is_export:
            # CA_EXP FlagHS: NO version_number grouping
            sort_cols = ['hs', 'version_date', 'valid_from', 'valid_to']
            ascending = [True, False, False, True]
            key_group = []  # No grouping key
        else:
            # Import FlagHS: groups by version_number
            sort_cols = ['version_number', 'hs', 'version_date', 'valid_from', 'valid_to']
            ascending = [True, True, False, False, True]
            key_group = ['version_number']
```

### 2. Updated `src/export_hs.py::generate_export_hs()`

Simplified to match QueryTable output:

```python
def generate_export_hs(nom_df: pd.DataFrame, txt_df: Optional[pd.DataFrame], config: AppConfig) -> pd.DataFrame:
    # Filter for active records only
    filtered_nom = nom_df[nom_df['hs_flag'] == '01-active'].copy()

    # Select columns matching query table
    output_df = pd.DataFrame({
        'hs': filtered_nom['number'].values,
        'level_id': filtered_nom['level_id'].values,
        'full_description': filtered_nom['full_description'].fillna('').values,
        'valid_from': filtered_nom['valid_from'].fillna('').values,
        'valid_to': filtered_nom['valid_to'].fillna('').values,
        'alternate_unit_1': filtered_nom['alternate_unit_1'].fillna('').values,
        'alternate_unit_2': filtered_nom['alternate_unit_2'].fillna('').values,
        'alternate_unit_3': filtered_nom['alternate_unit_3'].fillna('').values,
    })

    # Sort by HS code
    output_df = output_df.sort_values('hs').reset_index(drop=True)
    return output_df
```

### 3. Updated `app.py`

Export HS tab now calls:
```python
nom_df = flag_hs(nom_df, config, "NOM", is_export=True)
```

## Expected Output Format

The corrected Export HS output should now have:

**Columns:**
1. `hs` - Harmonized System code
2. `level_id` - Level in hierarchy (10, 20, 30, 40, 50)
3. `full_description` - Hierarchical description built from parents
4. `valid_from` - Validity start date (YYYY-MM-DD)
5. `valid_to` - Validity end date (YYYY-MM-DD)
6. `alternate_unit_1` - First alternate unit of measure
7. `alternate_unit_2` - Second alternate unit of measure
8. `alternate_unit_3` - Third alternate unit of measure

**Filters:**
- Only records with `hs_flag = '01-active'`
- Active means: `valid_to` year >= processing year

**Sort:**
- Ascending by `hs` code

## Key Differences from Previous Version

| Aspect | Previous (Incorrect) | Current (Corrected) |
|--------|---------------------|-------------------|
| **FlagHS Grouping** | Used version_number grouping | No grouping (global HS) |
| **Column Names** | Mixed names (HS_Code, Description, etc.) | Matches NOM columns (hs, full_description, etc.) |
| **Column Count** | 12 columns (with Country, Year, etc.) | 8 columns (core NOM fields only) |
| **Sorting** | May have had version_number influence | Pure HS code sort |

## Testing

To test the corrections:

1. Load Canada configuration
2. Upload `CA_EXP/input XML/HSCA_EXP_EN_NOM_I_00007001001.xml`
3. Run Export HS pipeline
4. Check output has:
   - 8 columns as listed above
   - Only active records
   - Sorted by HS code
   - Hierarchical descriptions built correctly

## Notes

The actual column names in the VBA Excel QueryTable might still be slightly different (e.g., capitalization, spaces). If the output structure is correct but column names need adjustment, those can be easily modified in `src/export_hs.py`.

The query table definition in the Excel workbook would have the exact column names, but since we couldn't read the file directly, we used the standard NOM column names that the query would pull from.

If specific column name changes are needed (e.g., "HS Code" instead of "hs"), please provide the exact expected column names and we can update the mapping.
