import pandas as pd
import logging
from typing import Optional
from .config import AppConfig

logger = logging.getLogger(__name__)

def generate_export_hs(nom_df: pd.DataFrame, txt_df: Optional[pd.DataFrame], config: AppConfig) -> pd.DataFrame:
    """
    Generate Export HS output format for ExpHSCA/ExpHSUS.

    The VBA QueryOutput creates a query table that:
    - Filters for ONLY 8-digit HS codes (level_id = 40 for CA, 50 for US)
    - Filters for active records only (hs_flag = '01-active')
    - Outputs 6 specific columns

    Expected output columns (CA format):
    1. Start date - Constructed from config.year + "01" (e.g., "202601" for year 2026)
    2. End date - Always "999912" (hardcoded)
    3. HS8_Code - 8-digit HS code
    4. HS8_Unit_of_Measure_Code - alternate_unit_1, defaults to "NMB" if empty
    5. HS8_Edesc - English description (full_description)
    6. HS8_Fdesc - French description (always empty)

    Expected output columns (US format):
    1. Start date - From XML valid_from in YYYYMM format
    2. End date - From XML valid_to in YYYYMM format
    3. HS8_Code - 8-digit HS code
    4. HS8_Unit_of_Measure_Code - alternate_unit_1, defaults to "NMB" if empty
    5. HS8_Edesc - English description (full_description)
    6. HS8_Fdesc - French description (always empty)

    Args:
        nom_df: Processed NOM dataframe with full_description and hs_flag
        txt_df: Optional TXT dataframe (not used)
        config: Configuration object

    Returns:
        DataFrame with 6 columns for 8-digit HS codes only
    """
    logger.info(f"Generating Export HS output for {config.country}")
    logger.info(f"Input NOM records: {len(nom_df)}")

    # Debug: Check what we have
    if 'hs_flag' in nom_df.columns:
        logger.info(f"hs_flag values: {nom_df['hs_flag'].value_counts().to_dict()}")
    else:
        logger.warning("hs_flag column not found in NOM dataframe!")

    if 'level_id' in nom_df.columns:
        logger.info(f"level_id values: {nom_df['level_id'].value_counts().to_dict()}")
        logger.info(f"level_id dtypes: {nom_df['level_id'].dtype}")
    else:
        logger.warning("level_id column not found in NOM dataframe!")

    # Filter for active records AND 8-digit codes only
    # Note: level_id differs by country: CA uses 40, US uses 50
    target_level = '50' if config.country.upper() == 'US' else '40'

    active_mask = nom_df['hs_flag'] == '01-active'
    level_mask = nom_df['level_id'].astype(str) == target_level

    logger.info(f"Records with hs_flag='01-active': {active_mask.sum()}")
    logger.info(f"Records with level_id={target_level}: {level_mask.sum()}")

    filtered_nom = nom_df[active_mask & level_mask].copy()

    logger.info(f"Active 8-digit HS records after filtering: {len(filtered_nom)}")

    # Create output with exact column names expected
    # Note: Date handling differs by country:
    # - CA: Uses config year + "01" for start, "999912" for end (ignores XML dates)
    # - US: Uses actual valid_from/valid_to dates from XML

    if config.country.upper() == 'CA':
        # Canada: Use config year for dates (matches VBA M code)
        start_date_value = f"{config.year}01"
        end_date_value = "999912"
        logger.info(f"CA format: Using Start date={start_date_value}, End date={end_date_value}")

        output_df = pd.DataFrame({
            'Start date': start_date_value,
            'End date': end_date_value,
            'HS8_Code': filtered_nom['number'].fillna('').values,
            'HS8_Unit_of_Measure_Code': filtered_nom['alternate_unit_1'].fillna('').values,
            'HS8_Edesc': filtered_nom['full_description'].fillna('').values,
            'HS8_Fdesc': '',  # Always empty for Export HS format
        })
    else:
        # US and others: Use actual dates from XML
        output_df = pd.DataFrame({
            'Start date': filtered_nom['valid_from'].fillna('').values,
            'End date': filtered_nom['valid_to'].fillna('').values,
            'HS8_Code': filtered_nom['number'].fillna('').values,
            'HS8_Unit_of_Measure_Code': filtered_nom['alternate_unit_1'].fillna('').values,
            'HS8_Edesc': filtered_nom['full_description'].fillna('').values,
            'HS8_Fdesc': '',  # Always empty for Export HS format
        })

        # Convert dates from YYYY-MM-DD to YYYYMM format (for US only)
        output_df['Start date'] = output_df['Start date'].apply(lambda x: x.replace('-', '')[:6] if x else '')
        output_df['End date'] = output_df['End date'].apply(lambda x: x.replace('-', '')[:6] if x else '')

    # Ensure HS8_Unit_of_Measure_Code always has a value
    # Default to 'NMB' (Number) if empty, matching VBA M code behavior
    empty_uom_count = output_df['HS8_Unit_of_Measure_Code'].isin(['', None]).sum()
    if empty_uom_count > 0:
        logger.info(f"Setting {empty_uom_count} empty UOM values to default 'NMB'")
    output_df['HS8_Unit_of_Measure_Code'] = output_df['HS8_Unit_of_Measure_Code'].replace('', 'NMB').fillna('NMB')

    # Sort by HS8_Code
    output_df = output_df.sort_values('HS8_Code').reset_index(drop=True)

    logger.info(f"Generated {len(output_df)} Export HS records (8-digit only)")

    return output_df
