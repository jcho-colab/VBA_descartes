import pandas as pd
import logging
import os
from datetime import datetime
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
    Generates the ZD14 DataFrame following M code logic:
    1. Filter DTR by date (version_date >= ZD14Date)
    2. Add header rows (-- and 0000000000)
    3. Join with NOM for descriptions and UOM
    4. Build all required columns
    """
    logger.info("Generating ZD14 Dataset...")

    if dtr_df.empty:
        logger.warning("DTR DataFrame is empty, cannot generate ZD14")
        return pd.DataFrame()

    # Filter by date if ZD14Date is configured
    filtered_dtr = dtr_df.copy()
    if hasattr(config, 'zd14_date') and config.zd14_date:
        filtered_dtr = filtered_dtr[
            pd.to_datetime(filtered_dtr['valid_from'], errors='coerce') >= pd.to_datetime(config.zd14_date, errors='coerce')
        ]

    # Add header rows with mainCG
    main_cg = config.main_cg if hasattr(config, 'main_cg') else ''
    year_start = f"{config.year}0101"

    header_rows = pd.DataFrame([
        {'hs': '--', 'country_group': main_cg, 'adValoremRate_percentage': 0,
         'specificRate_ratePerUOM': 0, 'specificRate_multiplier': None, 'specificRate_rateUOM': '',
         'valid_from': year_start, 'valid_to': '99991231', 'regulation': ''},
        {'hs': '0000000000', 'country_group': main_cg, 'adValoremRate_percentage': 0,
         'specificRate_ratePerUOM': 0, 'specificRate_multiplier': None, 'specificRate_rateUOM': '',
         'valid_from': year_start, 'valid_to': '99991231', 'regulation': ''}
    ])

    filtered_dtr = pd.concat([header_rows, filtered_dtr], ignore_index=True)

    # Add index for sorting later
    filtered_dtr['Index'] = range(len(filtered_dtr))

    # Join with NOM
    merged = pd.merge(
        filtered_dtr,
        nom_df[['number', 'full_description', 'alternate_unit_1']] if not nom_df.empty else pd.DataFrame(),
        left_on='hs',
        right_on='number',
        how='left'
    )

    # Sort by index to maintain order
    merged = merged.sort_values('Index').reset_index(drop=True)

    year_start_int = int(f"{config.year}0101")

    # Build ZD14 structure following M code column order
    def map_uom(u):
        if pd.isna(u) or u == '':
            return ""
        uom_str = str(u)
        return config.uom_dict.get(uom_str, uom_str)

    zd14 = pd.DataFrame({
        'Country': config.country,
        'HS Number': merged['hs'].fillna(''),
        'Date from': merged['valid_from'].apply(lambda d: format_date_from(d, year_start_int)),
        'Date to': merged['valid_to'].apply(format_date_to),
        'Lang 1': 'EN',
        'Desc 1': merged['full_description'].fillna(''),
        'Desc 2': '',
        'Desc 3': '',
        'Desc 4': '',
        'Desc 5': '',
        'Desc 6': '',
        'Desc 7': '',
        'Lang 2': 'ES',
        'Desc 21': merged['full_description'].fillna(''),  # Duplicate Desc 1
        'Desc 22': '',
        'Desc 23': '',
        'Desc 24': '',
        'Desc 25': '',
        'Desc 26': '',
        'Desc 27': '',
        'Unit of measure': merged['alternate_unit_1'].apply(map_uom) if 'alternate_unit_1' in merged.columns else '',
        'Restriction code': '',
        'Rate type': merged['country_group'].fillna(''),
        'Champ24': merged['valid_from'].apply(lambda d: format_date_from(d, year_start_int)),  # Duplicate Date from
        'Champ25': merged['valid_to'].apply(format_date_to),  # Duplicate Date to
        'Base rate %': merged['adValoremRate_percentage'].apply(format_rate),
        'Rate amount': merged['specificRate_ratePerUOM'].apply(format_rate),
        'Rate curr': '',
        'Rate qty': '',
        'Rate qty uom': '',
        'Spec App': '',
        'Cert Ori': merged['regulation'].fillna(''),
        'Cty Grp': ''
    })

    # Special handling for Brazil - clear rate amount
    if config.country == "BR":
        zd14['Rate amount'] = ''

    # Special replacement for US: 'T' -> 'TO' in UOM
    if config.country == "US":
        zd14['Unit of measure'] = zd14['Unit of measure'].replace('T', 'TO')

    logger.info(f"Generated ZD14 with {len(zd14)} rows")

    return zd14

def generate_capdr(dtr_df: pd.DataFrame, nom_df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """
    Generates the CAPDR DataFrame for Canada following M code logic:
    1. Start with ZD14 data
    2. Filter by mainCG
    3. Remove "--" and "0000000000"
    4. Replace mainCG with "PDR" in Rate type
    """
    logger.info("Generating CAPDR Dataset...")

    if config.country != "CA":
        logger.warning("CAPDR is only for Canada (CA)")
        return pd.DataFrame()

    # Generate base ZD14
    zd14 = generate_zd14(dtr_df, nom_df, config)

    if zd14.empty:
        return pd.DataFrame()

    # Filter by mainCG
    main_cg = config.main_cg if hasattr(config, 'main_cg') else ''
    capdr = zd14[zd14['Rate type'] == main_cg].copy()

    # Remove header rows (-- and 0000000000)
    capdr = capdr[
        (capdr['HS Number'] != '--') &
        (capdr['HS Number'] != '0000000000')
    ]

    # Replace mainCG with "PDR" in Rate type
    capdr['Rate type'] = 'PDR'

    logger.info(f"Generated CAPDR with {len(capdr)} rows")
    return capdr

def generate_mx6digits(dtr_df: pd.DataFrame, nom_df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """
    Generates the MX6Digits DataFrame for Mexico following M code logic:
    1. Start with ZD14 data
    2. Filter by mainCG
    3. Remove "--"
    4. Shorten HS to 6 digits
    5. Remove duplicates by HS Number
    """
    logger.info("Generating MX6Digits Dataset...")

    if config.country != "MX":
        logger.warning("MX6Digits is only for Mexico (MX)")
        return pd.DataFrame()

    # Generate base ZD14
    zd14 = generate_zd14(dtr_df, nom_df, config)

    if zd14.empty:
        return pd.DataFrame()

    # Filter by mainCG and remove "--"
    main_cg = config.main_cg if hasattr(config, 'main_cg') else ''
    mx6 = zd14[
        (zd14['Rate type'] == main_cg) &
        (zd14['HS Number'] != '--')
    ].copy()

    # Shorten HS to 6 digits
    mx6['HS Number'] = mx6['HS Number'].astype(str).str[:6]

    # Remove duplicates by HS Number
    mx6 = mx6.drop_duplicates(subset=['HS Number'], keep='first')

    logger.info(f"Generated MX6Digits with {len(mx6)} rows")
    return mx6

def generate_zzde(dtr_df: pd.DataFrame, nom_df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """
    Generates the ZZDE DataFrame for Canada following M code logic:
    1. Filter DTR by caMainCG
    2. Add header rows (-- and 0000000000)
    3. Calculate MFN $ = ratePerUOM / multiplier
    4. Join with NOM for STAT UOM
    5. Add all required columns
    """
    logger.info("Generating ZZDE Dataset...")

    if config.country != "CA":
        logger.warning("ZZDE is only for Canada (CA)")
        return pd.DataFrame()

    if dtr_df.empty:
        logger.warning("DTR DataFrame is empty, cannot generate ZZDE")
        return pd.DataFrame()

    # Filter by caMainCG
    main_cg = config.main_cg if hasattr(config, 'main_cg') else ''
    filtered_dtr = dtr_df[dtr_df['country_group'] == main_cg].copy()

    # Fill null multipliers with 1 for calculation
    filtered_dtr['specificRate_multiplier'] = filtered_dtr['specificRate_multiplier'].fillna(1)

    # Calculate MFN $ = ratePerUOM / multiplier
    filtered_dtr['mfn_amount'] = filtered_dtr['specificRate_ratePerUOM'] / filtered_dtr['specificRate_multiplier']

    # Add header rows
    year_start = f"{config.year}0101"
    header_rows = pd.DataFrame([
        {'hs': '--', 'adValoremRate_percentage': 0, 'mfn_amount': 0, 'specificRate_rateUOM': ''},
        {'hs': '0000000000', 'adValoremRate_percentage': 0, 'mfn_amount': 0, 'specificRate_rateUOM': ''}
    ])

    filtered_dtr = pd.concat([header_rows, filtered_dtr], ignore_index=True)
    filtered_dtr['Index'] = range(len(filtered_dtr))

    # Join with NOM
    merged = pd.merge(
        filtered_dtr,
        nom_df[['number', 'alternate_unit_1']] if not nom_df.empty else pd.DataFrame(),
        left_on='hs',
        right_on='number',
        how='left'
    )

    merged = merged.sort_values('Index').reset_index(drop=True)

    # Build ZZDE structure with exact column order from M code
    zzde = pd.DataFrame({
        'Cl.': 10,
        'Year': config.year,
        'Can HS No.': merged['hs'].fillna(''),
        'MFN %': merged['adValoremRate_percentage'].apply(format_rate),
        'MFN $': merged['mfn_amount'].apply(format_rate),
        'GPT %': 0,
        'GPT $': 0,
        'UST %': 0,
        'UST $': 0,
        'MEX %': 0,
        'MEX $': 0,
        'OTH %': 0,
        'OTH $': 0,
        'OTH2 %': 0,
        'OTH2 $': 0,
        'OTH3 %': 0,
        'OTH3 $': 0,
        '2450 %': 0,
        '2450 $': 0,
        '2460 %': 0,
        '2460 $': 0,
        '2475 %': 0,
        '2475 $': 0,
        'FREE %': 0,
        'FREE $': 0,
        'OTH4 %': 0,
        'OTH4 $': 0,
        'OTH5 %': 0,
        'OTH5 $': 0,
        'OTH6 %': 0,
        'OTH6 $': 0,
        'OTH7 %': 0,
        'OTH7 $': 0,
        'OTH8 %': 0,
        'OTH8 $': 0,
        'UOM %': '',
        'UOM $': merged['specificRate_rateUOM'].fillna(''),
        'STAT UOM': merged['alternate_unit_1'].fillna(''),
        'STAT1 UOM': '',
        'STAT1 QTY': 0,
        'STAT2 UOM': '',
        'STAT2 QTY': 0,
        'Mex-US %': 0,
        'Mex-US $': 0,
        'Rest Cd': '',
        'Date from': f"{config.year}0101",
        'Date to': '99991231'
    })

    logger.info(f"Generated ZZDE with {len(zzde)} rows")
    return zzde

def generate_zzdf(dtr_df: pd.DataFrame, nom_df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """
    Generates the ZZDF DataFrame for United States following M code logic:
    1. Filter DTR by usMainCG
    2. Add header rows (-- and 0000000000)
    3. Calculate GEN $ = ratePerUOM / multiplier
    4. Join with NOM for STAT UOM and STAT2 UOM
    5. Add all required columns
    """
    logger.info("Generating ZZDF Dataset...")

    if config.country != "US":
        logger.warning("ZZDF is only for United States (US)")
        return pd.DataFrame()

    if dtr_df.empty:
        logger.warning("DTR DataFrame is empty, cannot generate ZZDF")
        return pd.DataFrame()

    # Filter by usMainCG
    main_cg = config.main_cg if hasattr(config, 'main_cg') else ''
    filtered_dtr = dtr_df[dtr_df['country_group'] == main_cg].copy()

    # Fill null multipliers with 1 for calculation
    filtered_dtr['specificRate_multiplier'] = filtered_dtr['specificRate_multiplier'].fillna(1)

    # Calculate GEN $ = ratePerUOM / multiplier
    filtered_dtr['gen_amount'] = filtered_dtr['specificRate_ratePerUOM'] / filtered_dtr['specificRate_multiplier']

    # Add header rows
    header_rows = pd.DataFrame([
        {'hs': '--', 'adValoremRate_percentage': 0, 'gen_amount': 0, 'specificRate_rateUOM': ''},
        {'hs': '0000000000', 'adValoremRate_percentage': 0, 'gen_amount': 0, 'specificRate_rateUOM': ''}
    ])

    filtered_dtr = pd.concat([header_rows, filtered_dtr], ignore_index=True)
    filtered_dtr['Index'] = range(len(filtered_dtr))

    # Join with NOM for both alternate_unit_1 and alternate_unit_2
    merged = pd.merge(
        filtered_dtr,
        nom_df[['number', 'alternate_unit_1', 'alternate_unit_2']] if not nom_df.empty else pd.DataFrame(),
        left_on='hs',
        right_on='number',
        how='left'
    )

    merged = merged.sort_values('Index').reset_index(drop=True)

    # Build ZZDF structure with exact column order from M code
    zzdf = pd.DataFrame({
        'Cl.': 10,
        'Year': config.year,
        'US HS No.': merged['hs'].fillna(''),
        'GEN %': merged['adValoremRate_percentage'].apply(format_rate),
        'GEN $': merged['gen_amount'].apply(format_rate),
        'CAN %': 0,
        'CAN $': 0,
        'MEX %': 0,
        'MEX $': 0,
        'UMX %': 0,
        'UMX $': 0,
        'OTH %': 0,
        'OTH $': 0,
        'OTH1 %': 0,
        'OTH1 $': 0,
        'OTH2 %': 0,
        'OTH2 $': 0,
        'OTH3 %': 0,
        'OTH3 $': 0,
        'UOM %': '',
        'UOM $': merged['specificRate_rateUOM'].fillna(''),
        'STAT UOM': merged['alternate_unit_1'].fillna(''),
        'STAT QTY': 0,
        'STAT2 UOM': merged['alternate_unit_2'].fillna(''),
        'STAT2 QTY': 0,
        'Restr': ''
    })

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

def export_xlsx(df: pd.DataFrame, output_dir: str, prefix: str, country: str) -> str:
    """
    Exports DataFrame to a single Excel file (XLSX).
    Replicates ExportXLSX logic from CA_EXP VBA.

    Args:
        df: DataFrame to export
        output_dir: Output directory path
        prefix: File prefix (e.g., "ExpHSCA")
        country: Country code

    Returns:
        Path to exported file
    """
    if df.empty:
        logger.warning(f"DataFrame is empty, skipping export for {prefix}")
        return None

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    version = 1
    while os.path.exists(os.path.join(output_dir, f"UPLOAD {prefix} V{version} {datetime.now().strftime('%Y%m%d')}.xlsx")):
        version += 1

    file_name = f"UPLOAD {prefix} V{version} {datetime.now().strftime('%Y%m%d')}.xlsx"
    path = os.path.join(output_dir, file_name)

    df.to_excel(path, index=False, engine='openpyxl')

    logger.info(f"Exported {path} with {len(df)} rows")

    return path
