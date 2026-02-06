# Debugging: Empty DataFrame Issue

## Problem
The Export HS pipeline was generating an empty DataFrame when it should have produced ~4981 records with 8-digit HS codes.

## Root Cause

The issue was a **column name mismatch** between NOM and DTR data structures:

1. **NOM XML uses**: `number`, `validity_begin`, `validity_end`
2. **DTR XML uses**: `hs`, `valid_from`, `valid_to`
3. **Processing functions expected**: `hs`, `valid_from`, `valid_to`

### The Problem Flow

```
1. app.py calls: cleanse_hs(nom_df, 'number')
   → Cleanses the 'number' column but doesn't create 'hs'

2. app.py calls: filter_by_chapter(nom_df, config)
   → Looks for 'hs' column, doesn't find it
   → Returns empty or unchanged dataframe

3. app.py calls: flag_hs(nom_df, config, "NOM", is_export=True)
   → Tries to sort by 'hs' column
   → 'hs' column doesn't exist or is empty
   → Creates empty string columns
   → All records fail filtering

4. generate_export_hs() tries to filter
   → No valid hs_flag='01-active' records
   → Empty DataFrame!
```

## Solution

Added column mapping in three places:

### 1. flag_hs() Function (src/process.py)

```python
# Map 'number' to 'hs' for consistency with DTR
if 'number' in df.columns and 'hs' not in df.columns:
    df['hs'] = df['number']
    logger.info(f"Mapped number -> hs for NOM data")
```

This ensures the 'hs' column exists before sorting and flagging.

### 2. filter_by_chapter() Function (src/process.py)

```python
# Check for 'hs' or 'number' column
hs_col = None
if 'hs' in df.columns:
    hs_col = 'hs'
elif 'number' in df.columns:
    hs_col = 'number'
else:
    logger.warning("No hs or number column found, skipping chapter filter")
    return df
```

This makes the function work with both column names.

### 3. Enhanced Debug Logging

Added comprehensive logging to track:
- Input record counts at each stage
- Column availability
- Flag distribution (01-active, 02-invalid, 03-duplicate)
- Level_id distribution
- Filter results

#### In flag_hs():
```python
logger.info(f"flag_hs called: doc_type={doc_type}, is_export={is_export}, rows={len(df)}")
logger.info(f"Available columns: {list(df.columns)}")
# ... mapping happens ...
logger.info(f"Flag distribution: {flag_counts}")
```

#### In generate_export_hs():
```python
logger.info(f"Input NOM records: {len(nom_df)}")
logger.info(f"hs_flag values: {nom_df['hs_flag'].value_counts().to_dict()}")
logger.info(f"level_id values: {nom_df['level_id'].value_counts().to_dict()}")
logger.info(f"Records with hs_flag='01-active': {active_mask.sum()}")
logger.info(f"Records with level_id=40: {level_40_mask.sum()}")
logger.info(f"Active 8-digit HS records after filtering: {len(filtered_nom)}")
```

## Expected Behavior After Fix

With proper logging, you should see:

```
INFO: flag_hs called: doc_type=NOM, is_export=True, rows=7617
INFO: Available columns: ['number', 'level_id', 'validity_begin', 'validity_end', ...]
INFO: Mapped validity_begin -> valid_from
INFO: Mapped validity_end -> valid_to
INFO: Mapped date_of_physical_update -> version_date
INFO: Mapped number -> hs for NOM data
INFO: Flag distribution: {'01-active': 6255, '02-invalid': 1362}
INFO: Generating Export HS output for CA
INFO: Input NOM records: 7617
INFO: hs_flag values: {'01-active': 6255, '02-invalid': 1362}
INFO: level_id values: {40: 6255, 20: 700, 10: 99, 30: 563}
INFO: Records with hs_flag='01-active': 6255
INFO: Records with level_id=40: 6255
INFO: Active 8-digit HS records after filtering: 4981
INFO: Generated 4981 Export HS records (8-digit only)
```

## Key Insights

1. **NOM and DTR have different schemas** - Must map column names
2. **Column mapping must happen BEFORE filtering/flagging** - Otherwise functions fail
3. **Debug logging is essential** - Shows exactly where data is lost
4. **Level 40 = 8-digit codes** - This is the key filter for export HS

## Files Modified

1. `src/process.py`:
   - Added column mapping in `flag_hs()` (number → hs)
   - Added debug logging in `flag_hs()`
   - Updated `filter_by_chapter()` to handle both 'hs' and 'number'

2. `src/export_hs.py`:
   - Added extensive debug logging
   - Added separate filter checks to identify which filter is failing

## Testing

To verify the fix works:

1. Run the Export HS pipeline
2. Check the console logs for:
   - "Mapped number -> hs for NOM data"
   - "Flag distribution: {'01-active': 6255, ...}"
   - "Active 8-digit HS records after filtering: 4981"
3. Verify output file has ~4982 rows with 6 columns
4. Verify all HS8_Code values are 8 digits

## Prevention

To prevent similar issues in future:

1. **Always log column names** at function entry
2. **Map columns early** before any processing
3. **Check expected columns exist** before using them
4. **Add debug logging** to track data flow
5. **Test with actual XML files** not just mock data
