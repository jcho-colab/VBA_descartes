import pandas as pd
import logging
import os
from .config import AppConfig

logger = logging.getLogger(__name__)

def generate_zd14(dtr_df: pd.DataFrame, nom_df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """
    Generates the ZD14 DataFrame by joining DTR and NOM data and mapping columns.
    """
    logger.info("Generating ZD14 Dataset...")
    
    # 1. Join DTR with NOM to get Description and UOM
    # Key: DTR.hs == NOM.number (Wait, NOM has number and id. number seems to be the code.)
    # Ensure processed 'hs' in DTR matches NOM 'number'.
    # If DTR hs was cleansed (no '00' prefix), NOM number must also be cleanse-compatible or not cleansed?
    # VBA ProcessHS only cleansed DTR/NOM if they had leading 00.
    # NOM usually doesn't have leading 00 in the sample (010239...). DTR sample (16055...) also no leading 00.
    # But checking raw usage.
    
    # Left join DTR -> NOM
    merged = pd.merge(
        dtr_df,
        nom_df[['number', 'full_description', 'alternate_unit_1']], 
        left_on='hs', 
        right_on='number', 
        how='left'
    )
    
    # 2. Construct ZD14 Columns
    zd14 = pd.DataFrame()
    
    # Static / Direct Mappings
    zd14['Country'] = config.country
    zd14['HS Number'] = merged['hs']
    
    year_start_int = int(f"{config.year}0101")
    
    # Date formatting: YYYYMMDD and Clamp to config.year
    def fmt_date_from(d):
        if pd.isna(d): return ""
        s = str(d).replace("-", "")
        # Clamp: if date < year_start, use year_start
        try:
            val_int = int(s[:8])
            if val_int < year_start_int:
                return str(year_start_int)
            return str(val_int)
        except:
            return s[:8]

    def fmt_date_to(d):
        if pd.isna(d): return ""
        s = str(d).replace("-", "")
        try:
            val_int = int(s[:8])
            # If 9999, ensure it ends 1231
            if str(val_int).startswith("9999"):
                return "99991231"
            return str(val_int)
        except:
            return s[:8]
        
    zd14['Date from'] = merged['valid_from'].apply(fmt_date_from)
    zd14['Date to'] = merged['valid_to'].apply(fmt_date_to)
    
    zd14['Lang 1'] = "EN"
    zd14['Desc 1'] = merged['full_description']
    
    # Empty Descs
    for i in range(2, 8):
        zd14[f'Desc {i}'] = ""
        
    zd14['Lang 2'] = "ES" # Hardcoded in sample?
    
    for i in range(21, 28):
         zd14[f'Desc {i}'] = ""
         
    # Unit of measure
    # NOM.alternate_unit_1 mapped via UOMDict
    def map_uom(u):
        if pd.isna(u): return ""
        return config.uom_dict.get(u, u)
        
    zd14['Unit of measure'] = merged['alternate_unit_1'].apply(map_uom)
    
    zd14['Restriction code'] = ""
    
    # Rate type -> Country Group in sample ( _DNZ1 )
    zd14['Rate type'] = merged['country_group'] # or concat_cg_drt? Sample shows _DNZ1 which is CG.
    
    # Champ24/25 -> Dates again? matches sample
    zd14['Champ24'] = zd14['Date from']
    zd14['Champ25'] = zd14['Date to']
    
    # Rates
    # adValoremRate_percentage -> Base rate %
    # specificRate_ratePerUOM -> Rate amount
    # Defaults to 0 if NaN
    # Rates formatting
    # Force 0.0 format for comparison matching expected output
    def fmt_rate(r):
        try:
            val = float(r) if not pd.isna(r) else 0.0
            if val == 0: return "0.0" # Explicit '0.0' for 0
            # If it's an integer value, show matches? 
            # Sample shows 0.0. Let's assume standard float but maybe stripped? 
            # Actually sample '0.0' suggests always at least one decimal.
            return f"{val:.1f}".rstrip('0').rstrip('.') if val % 1 != 0 else f"{val:.1f}"
        except:
            return "0.0"

    zd14['Base rate %'] = merged['adValoremRate_percentage'].apply(fmt_rate)
    zd14['Rate amount'] = merged['specificRate_ratePerUOM'].apply(fmt_rate)
    
    zd14['Rate curr'] = "" # Need to check if specificRate has currency?
    zd14['Rate qty'] = ""
    zd14['Rate qty uom'] = ""
    zd14['Spec App'] = ""
    
    # Cert Ori -> regulation?
    zd14['Cert Ori'] = merged['regulation'].fillna("")
    
    zd14['Cty Grp'] = "" # Empty in sample
    
    # formatting needed? 
    # Ensure Rate Amount/Base Rate are numeric? Or strings?
    # Sample has "0". 
    
    # Replace US 'T' -> 'TO' in UOM (Handled by general UOM dict or special case)
    if config.country == "US":
        zd14['Unit of measure'] = zd14['Unit of measure'].replace('T', 'TO')
        
    return zd14

def export_csv_split(df: pd.DataFrame, output_dir: str, prefix: str, max_rows: int = 1000000):
    """
    Exports DataFrame to CSVs, splitting if max_rows exceeded.
    Replicates ExportCSV logic.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    total_rows = len(df)
    start_row = 0
    file_idx = 1
    
    # Determine base filename version
    # The prompt implies overwriting or new version? 
    # VBA logic searches for existing versions.
    # We will just use V1 for now or a timestamp. 
    # User said "Output CSV/NZ UPLOAD _ZD14 V1-1.csv".
    # We will try to match "V1".
    
    base_name = f"{prefix} V1"
    
    while start_row < total_rows:
        end_row = min(start_row + max_rows, total_rows)
        chunk = df.iloc[start_row:end_row]
        
        file_name = f"{base_name}-{file_idx}.csv"
        path = os.path.join(output_dir, file_name)
        
        # Format: Semicolon delimiter? Sample has semicolons.
        # Header only in first file?
        # VBA: Copy-Paste header row for every new workbook. So Yes, Header in all.
        
        chunk.to_csv(path, sep=';', index=False, encoding='utf-8-sig') # UTF8-BOM (utf-8-sig) or standard? VBA says xlCSVUTF8.
        
        logger.info(f"Exported {path} with {len(chunk)} rows.")
        
        start_row = end_row
        file_idx += 1
