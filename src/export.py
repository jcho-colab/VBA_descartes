import pandas as pd
import logging
import os
from .config import AppConfig

logger = logging.getLogger(__name__)

def format_rate(r, decimal_places: int = 1) -> str:
    """Format rate values for CSV output."""
    try:
        if pd.isna(r) or r == '' or r is None:
            return "0"
        val = float(r)
        if val == 0:
            return "0"
        # Format with specified decimal places, remove trailing zeros
        formatted = f"{val:.{decimal_places}f}".rstrip('0').rstrip('.')
        return formatted if formatted else "0"
    except:
        return "0"

def format_date_from(d, year_start_int: int) -> str:
    """Format valid_from date to YYYYMMDD, clamping to year start."""
    if pd.isna(d) or d == '':
        return ""
    s = str(d).replace("-", "").replace(" ", "")[:8]
    try:
        val_int = int(s)
        if val_int < year_start_int:
            return str(year_start_int)
        return str(val_int)
    except:
        return s

def format_date_to(d) -> str:
    """Format valid_to date to YYYYMMDD."""
    if pd.isna(d) or d == '':
        return ""
    s = str(d).replace("-", "").replace(" ", "")[:8]
    try:
        val_int = int(s)
        # If 9999, ensure it ends 1231
        if str(val_int).startswith("9999"):
            return "99991231"
        return str(val_int)
    except:
        return s

def generate_zd14(dtr_df: pd.DataFrame, nom_df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """
    Generates the ZD14 DataFrame by joining DTR and NOM data and mapping columns.
    """
    logger.info("Generating ZD14 Dataset...")
    
    if dtr_df.empty:
        logger.warning("DTR DataFrame is empty, cannot generate ZD14")
        return pd.DataFrame()
    
    # 1. Join DTR with NOM to get Description and UOM
    merged = pd.merge(
        dtr_df,
        nom_df[['number', 'full_description', 'alternate_unit_1']] if not nom_df.empty else pd.DataFrame(), 
        left_on='hs', 
        right_on='number', 
        how='left'
    )
    
    # 2. Construct ZD14 Columns
    zd14 = pd.DataFrame()
    
    # Static / Direct Mappings - use .values to avoid index issues
    zd14['Country'] = config.country
    zd14['HS Number'] = merged['hs'].values
    
    year_start_int = int(f"{config.year}0101")
    
    # Date formatting
    zd14['Date from'] = merged['valid_from'].apply(lambda d: format_date_from(d, year_start_int)).values
    zd14['Date to'] = merged['valid_to'].apply(format_date_to).values
    
    zd14['Lang 1'] = "EN"
    zd14['Desc 1'] = merged['full_description'].fillna("").values
    
    # Empty Descs
    for i in range(2, 8):
        zd14[f'Desc {i}'] = ""
        
    zd14['Lang 2'] = "ES" # Hardcoded in sample
    
    for i in range(21, 28):
         zd14[f'Desc {i}'] = ""
         
    # Unit of measure - mapped via UOMDict
    def map_uom(u):
        if pd.isna(u) or u == '':
            return ""
        uom_str = str(u)
        return config.uom_dict.get(uom_str, uom_str)
        
    zd14['Unit of measure'] = merged['alternate_unit_1'].apply(map_uom) if 'alternate_unit_1' in merged.columns else ""
    
    zd14['Restriction code'] = ""
    
    # Rate type -> Country Group
    zd14['Rate type'] = merged['country_group'].fillna("")
    
    # Champ24/25 -> Dates again
    zd14['Champ24'] = zd14['Date from']
    zd14['Champ25'] = zd14['Date to']
    
    # Rates
    zd14['Base rate %'] = merged['adValoremRate_percentage'].apply(format_rate) if 'adValoremRate_percentage' in merged.columns else "0"
    zd14['Rate amount'] = merged['specificRate_ratePerUOM'].apply(format_rate) if 'specificRate_ratePerUOM' in merged.columns else "0"
    
    # Special handling for Brazil - clear rate amount
    if config.country == "BR":
        zd14['Rate amount'] = ""
    
    zd14['Rate curr'] = ""
    zd14['Rate qty'] = ""
    zd14['Rate qty uom'] = ""
    zd14['Spec App'] = ""
    
    # Cert Ori -> regulation
    zd14['Cert Ori'] = merged['regulation'].fillna("") if 'regulation' in merged.columns else ""
    
    zd14['Cty Grp'] = ""
    
    # Special replacement for country 'US': 'T' -> 'TO' in UOM
    if config.country == "US":
        zd14['Unit of measure'] = zd14['Unit of measure'].replace('T', 'TO')
    
    logger.info(f"Generated ZD14 with {len(zd14)} rows")
    
    return zd14

def generate_capdr(dtr_df: pd.DataFrame, nom_df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """
    Generates the CAPDR DataFrame for Canada.
    """
    logger.info("Generating CAPDR Dataset...")
    
    if config.country != "CA":
        logger.warning("CAPDR is only for Canada (CA)")
        return pd.DataFrame()
    
    # CAPDR typically has similar structure to ZD14 but with Canada-specific fields
    # Placeholder implementation - needs specific mapping based on requirements
    capdr = generate_zd14(dtr_df, nom_df, config)
    
    logger.info(f"Generated CAPDR with {len(capdr)} rows")
    return capdr

def generate_mx6digits(dtr_df: pd.DataFrame, nom_df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """
    Generates the MX6Digits DataFrame for Mexico.
    """
    logger.info("Generating MX6Digits Dataset...")
    
    if config.country != "MX":
        logger.warning("MX6Digits is only for Mexico (MX)")
        return pd.DataFrame()
    
    # MX6Digits - specific format for Mexico
    # Placeholder implementation
    mx6 = generate_zd14(dtr_df, nom_df, config)
    
    logger.info(f"Generated MX6Digits with {len(mx6)} rows")
    return mx6

def generate_zzde(dtr_df: pd.DataFrame, nom_df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """
    Generates the ZZDE DataFrame for Canada.
    """
    logger.info("Generating ZZDE Dataset...")
    
    if config.country != "CA":
        logger.warning("ZZDE is only for Canada (CA)")
        return pd.DataFrame()
    
    # ZZDE - another Canada-specific format
    zzde = generate_zd14(dtr_df, nom_df, config)
    
    logger.info(f"Generated ZZDE with {len(zzde)} rows")
    return zzde

def generate_zzdf(dtr_df: pd.DataFrame, nom_df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """
    Generates the ZZDF DataFrame for United States.
    """
    logger.info("Generating ZZDF Dataset...")
    
    if config.country != "US":
        logger.warning("ZZDF is only for United States (US)")
        return pd.DataFrame()
    
    # ZZDF - US-specific format with T->TO replacement
    zzdf = generate_zd14(dtr_df, nom_df, config)
    
    # Additional ZZDF-specific processing
    # Replace 'T' with 'TO' in all columns (VBA does this for entire table)
    for col in zzdf.columns:
        zzdf[col] = zzdf[col].apply(lambda x: 'TO' if x == 'T' else x)
    
    logger.info(f"Generated ZZDF with {len(zzdf)} rows")
    return zzdf

def find_next_version(output_dir: str, prefix: str) -> int:
    """Find the next available version number for CSV exports."""
    if not os.path.exists(output_dir):
        return 1
    
    version = 1
    while os.path.exists(os.path.join(output_dir, f"{prefix} V{version}-1.csv")):
        version += 1
    
    return version

def export_csv_split(df: pd.DataFrame, output_dir: str, prefix: str, max_rows: int = 1000000, version: int = None):
    """
    Exports DataFrame to CSVs, splitting if max_rows exceeded.
    Replicates ExportCSV logic.
    """
    if df.empty:
        logger.warning(f"DataFrame is empty, skipping export for {prefix}")
        return
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Find next version if not specified
    if version is None:
        version = find_next_version(output_dir, prefix)
        
    total_rows = len(df)
    start_row = 0
    file_idx = 1
    
    base_name = f"{prefix} V{version}"
    
    exported_files = []
    
    while start_row < total_rows:
        end_row = min(start_row + max_rows, total_rows)
        chunk = df.iloc[start_row:end_row]
        
        file_name = f"{base_name}-{file_idx}.csv"
        path = os.path.join(output_dir, file_name)
        
        # Format: Semicolon delimiter, UTF-8 with BOM
        chunk.to_csv(path, sep=';', index=False, encoding='utf-8-sig', lineterminator='\r\n')
        
        logger.info(f"Exported {path} with {len(chunk)} rows")
        exported_files.append(path)
        
        start_row = end_row
        file_idx += 1
    
    return exported_files
