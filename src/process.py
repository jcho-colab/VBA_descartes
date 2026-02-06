import pandas as pd
import logging
from typing import List, Dict, Set, Optional
from .config import AppConfig

logger = logging.getLogger(__name__)

def replace_chars(text: str) -> str:
    """Replace semicolons with dots for CSV compatibility."""
    if pd.isna(text):
        return ""
    return str(text).replace(';', '.')

def cleanse_hs(df: pd.DataFrame, col_name: str = 'hs') -> pd.DataFrame:
    """Removes leading '00' from HS codes."""
    if col_name in df.columns:
        # VBA: Right(Value, Len(Value) - 2) if starts with 00
        # In Python: if starts with 00, slice [2:]
        df[col_name] = df[col_name].apply(lambda x: x[2:] if isinstance(x, str) and x.startswith('00') else x)
    return df

def filter_by_chapter(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """Filters HS codes to include only chapters in chapter_list."""
    if 'hs' not in df.columns:
        return df
    
    if not config.chapter_list:
        logger.warning("No chapter list defined, skipping chapter filter")
        return df
        
    def is_valid_chapter(hs):
        if not isinstance(hs, str) or len(hs) < 2: 
            return False
        chapter = hs[:2]
        return chapter in config.chapter_list

    original_count = len(df)
    df_filtered = df[df['hs'].apply(is_valid_chapter)].copy()
    filtered_count = len(df_filtered)
    
    logger.info(f"Chapter filter: {original_count} -> {filtered_count} rows (removed {original_count - filtered_count})")
    
    return df_filtered

def filter_active_country_groups(dtr_df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """Filters DTR data to keep only active country groups defined in config."""
    # Active groups are those without "remove" in Comment column of RateType table
    # We need to extract this list from config.rate_type_defs
    
    if config.rate_type_defs.empty:
        logger.warning("No RateType definitions found. Skipping Country Group filter.")
        return dtr_df

    # Extract active groups
    # Table columns: "Descartes CG", "Comment"
    # VBA logic: if Comment != "remove"
    
    active_groups = []
    if "Descartes CG" in config.rate_type_defs.columns:
        for _, row in config.rate_type_defs.iterrows():
            comment = row.get("Comment", "")
            if comment != "remove":
                active_groups.append(row["Descartes CG"])
    
    # Also we need to form "concat_cg_drt" logic if needed, but VBA filters DTR by "concat_cg_drt" match?
    # VBA: GetOppositeList of ActiveCountryGroupList against 'concat_cg_drt' and delete.
    # Note: 'concat_cg_drt' = country_group + " " + duty_rate_type
    
    # Let's recreate 'concat_cg_drt' column
    dtr_df['concat_cg_drt'] = dtr_df['country_group'] + " " + dtr_df['duty_rate_type']
    
    # Filter
    # We keep rows where concat_cg_drt is in active_groups
    # Wait, the VBA logic compares 'concat_cg_drt' with 'Descartes CG'.
    # So 'Descartes CG' in the config table IS the 'country_group + duty_rate_type' string.
    
    return dtr_df[dtr_df['concat_cg_drt'].isin(active_groups)].copy()

def flag_hs(df: pd.DataFrame, config: AppConfig, doc_type: str, is_export: bool = False) -> pd.DataFrame:
    """
    Flags HS codes as 01-active, 02-invalid, 03-duplicate.
    Replicates FlagHS logic.

    Args:
        df: DataFrame to flag
        config: Configuration object
        doc_type: "DTR" or "NOM"
        is_export: If True, use Export HS flagging (no version_number grouping)
    """
    # Sort keys
    # DTR: country_group, hs, version_date (desc), valid_from (desc), valid_to (asc), rates (desc)

    # Ensure date columns are datetime for proper sorting if possible, or string sort YYYY-MM-DD works too
    # The XML dates are usually YYYY-MM-DD.

    sort_cols = []
    ascending = []

    if doc_type == "DTR":
        sort_cols = ['country_group', 'hs', 'version_date', 'valid_from', 'valid_to']
        ascending = [True, True, False, False, True]

        # Add rate columns if they exist
        rate_cols = ['adValoremRate_percentage', 'specificRate_ratePerUOM', 'compoundRate_percentage']
        for rc in rate_cols:
            if rc in df.columns:
                sort_cols.append(rc)
                ascending.append(False)

        key_group = ['country_group'] # We flag uniqueness per country_group

    elif doc_type == "NOM":
        # Import NOM: groups by version_number
        # Export NOM (CA_EXP): NO version_number grouping, just global HS
        if is_export:
            # CA_EXP FlagHS: sort by hs, version_date, valid_from, valid_to only
            # No version_number key
            sort_cols = ['hs', 'version_date', 'valid_from', 'valid_to']
            ascending = [True, False, False, True]
            key_group = []  # No grouping key - flag globally per HS
        else:
            # Import FlagHS for NOM (original behavior)
            sort_cols = ['version_number', 'hs', 'version_date', 'valid_from', 'valid_to']
            ascending = [True, True, False, False, True]
            key_group = ['version_number']

    else:
        return df

    # Column Mapping for NOM (standardize to DTR/VBA expected names)
    if doc_type == "NOM":
        # Map: validity_begin -> valid_from, validity_end -> valid_to, date_of_physical_update -> version_date
        mappings = {
            'validity_begin': 'valid_from',
            'validity_end': 'valid_to',
            'date_of_physical_update': 'version_date'
        }
        for old, new in mappings.items():
            if old in df.columns and new not in df.columns:
                df[new] = df[old]
                
    # Apply Sort
    # Fill N/As to avoid sort issues?
    for col in sort_cols:
        if col not in df.columns:
            # If version_number is missing in NOM, fill with 0 or empty
            df[col] = "" # Create empty if missing
            
    df = df.sort_values(by=sort_cols, ascending=ascending)
    
    # Flagging Logic
    # Iterate groups defined by key_group
    # Within each group, iterate HS.
    # First occurrence of HS -> Active/Invalid check
    # Subsequent -> Duplicate

    # Vectorized approach:
    # Mark duplicates based on [key_group + 'hs']
    # Keep='first' means first is unique, others are duplicates

    # For export without grouping key, just check HS duplicates globally
    if key_group:
        subset_cols = key_group + ['hs']
    else:
        subset_cols = ['hs']
    df['is_duplicate'] = df.duplicated(subset=subset_cols, keep='first')
    
    def determine_flag(row):
        if row['is_duplicate']:
            return "03-duplicate"
        
        # Check valid_to year
        valid_to = str(row.get('valid_to', ''))
        # If valid_to starts with year >= config.Year -> Active
        # Else Invalid
        # format YYYY-MM-DD
        if len(valid_to) >= 4:
            year = valid_to[:4]
            # If ValidTo is huge (e.g. 9999), it's active
            if year >= config.year:
                return "01-active"
            else:
                return "02-invalid"
        return "02-invalid" # specific default?

    df['hs_flag'] = df.apply(determine_flag, axis=1)
    df.drop(columns=['is_duplicate'], inplace=True)
    
    return df

def build_descriptions(nom_df: pd.DataFrame) -> pd.DataFrame:
    """
    Replicates CompleteDescription.
    Builds full description by traversing parent_id.
    
    VBA Logic:
    - Level 10 (chapter): Use official_description as-is
    - Level 20+ (including 50): Prepend parent's full_description with "---"
    - Level 50 is not added to the dictionary for OTHERS to reference, but level 50 items
      themselves still need to build their full description from parents
    """
    logger.info(f"Building hierarchical descriptions for {len(nom_df)} NOM records...")
    
    # Build a complete map of ALL items first (including level 50) for lookups
    data_map = {}
    for _, row in nom_df.iterrows():
        rid = row.get('id')
        pid = row.get('parent_id')
        desc = row.get('official_description', '')
        lvl = str(row.get('level_id', ''))
        
        if pd.notna(rid):
            data_map[str(rid)] = {
                'pid': str(pid) if pd.notna(pid) else None,
                'desc': replace_chars(desc),
                'lvl': lvl
            }
            
    # Cache for full descriptions to avoid re-traversing
    full_desc_cache = {}
    
    def get_full_desc(curr_id: str, depth: int = 0) -> str:
        """Recursively build full description from parent chain."""
        # Prevent infinite recursion
        if depth > 20:
            logger.warning(f"Max recursion depth reached for ID {curr_id}")
            return ""
            
        if curr_id not in data_map:
            return ""
        
        # Return cached if available
        if curr_id in full_desc_cache:
            return full_desc_cache[curr_id]
        
        item = data_map[curr_id]
        desc = item['desc']
        
        # VBA: If level=10 (chapter), full_desc = official_desc only
        if item['lvl'] == '10':
            full_desc_cache[curr_id] = desc
            return desc
        
        # For all other levels (20, 30, 40, 50): parent_full_desc + "---" + current_desc
        pid = item['pid']
        if pid and pid != curr_id:  # Avoid self-reference
            parent_desc = get_full_desc(pid, depth + 1)
            if parent_desc:
                full = f"{parent_desc}---{desc}"
            else:
                full = desc
        else:
            full = desc
            
        full_desc_cache[curr_id] = full
        return full

    # Build full descriptions for all items in the dataframe
    full_descriptions = []
    for _, row in nom_df.iterrows():
        rid = row.get('id')
        if pd.notna(rid) and str(rid) in data_map:
            full_descriptions.append(get_full_desc(str(rid)))
        else:
            # Fallback for missing entries
            full_descriptions.append(replace_chars(row.get('official_description', '')))

    nom_df['full_description'] = full_descriptions
    
    logger.info(f"Completed building descriptions")
    
    return nom_df

