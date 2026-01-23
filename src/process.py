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

def flag_hs(df: pd.DataFrame, config: AppConfig, doc_type: str) -> pd.DataFrame:
    """
    Flags HS codes as 01-active, 02-invalid, 03-duplicate.
    Replicates FlagHS logic.
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
        # NOM sorting: version_number?, hs, ... (VBA says sKey2="version_number", sort by sKey2 asc, HS asc...)
        # Actually VBA FlagHS for NOM:
        # Key: .Parent.ListColumns(sKey2).Range -> version_number
        # .SortFields.Add Key=hs
        # ... same date sorts ...
        
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
    
    subset_cols = key_group + ['hs']
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
    """
    # Create a dictionary of id -> official_description
    # We might need to handle 'hs_flag' logic first (VBA puts duplicates at bottom, assumes top is correct)
    # But usually we just want to look up descriptions by ID.
    
    # We need a recursive look up.
    # Since dataframe lookups are slow, convert to dict.
    
    # Filter out level_id=50? (VBA: If Not level_id=50 Then Add to Dict)
    
    # Dict: ID -> {parent_id: ..., desc: ...}
    data_map = {}
    for _, row in nom_df.iterrows():
        rid = row.get('id')
        pid = row.get('parent_id')
        desc = row.get('official_description', '')
        lvl = str(row.get('level_id', ''))
        
        if lvl != '50':
            data_map[rid] = {'pid': pid, 'desc': desc, 'lvl': lvl}
            
    # Cache for full descriptions to avoid re-traversing
    full_desc_cache = {}
    
    def get_full_desc(curr_id):
        if curr_id not in data_map:
            return ""
        
        if curr_id in full_desc_cache:
            return full_desc_cache[curr_id]
        
        item = data_map[curr_id]
        desc = str(item['desc']).replace(';', '.') # Replace ; with .
        
        # VBA: If level=10, full_desc = official_desc
        if item['lvl'] == '10':
            full_desc_cache[curr_id] = desc
            return desc
        
        # Else: parent_full_desc + "---" + current_desc
        pid = item['pid']
        parent_desc = get_full_desc(pid)
        
        if parent_desc:
            full = f"{parent_desc}---{desc}"
        else:
            full = desc
            
        full_desc_cache[curr_id] = full
        return full

    # Apply to DataFrame
    full_descriptions = []
    for _, row in nom_df.iterrows():
        rid = row.get('id')
        # If level is 10 or whatever, logic handles it inside get_full_desc
        # But we need to call it for every row (even duplicates? VBA effectively does it for all rows)
        
        # If ID is missing or level 50, maybe just use own desc?
        if rid in data_map:
            full_descriptions.append(get_full_desc(rid))
        else:
            # Fallback
            full_descriptions.append(str(row.get('official_description', '')).replace(';', '.'))

    nom_df['full_description'] = full_descriptions
    return nom_df

