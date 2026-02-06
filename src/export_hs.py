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
    - Outputs country-specific columns

    Expected output columns (CA format):
    1. Start date - Constructed from config.year + "01" (e.g., "200001" for year 2000)
    2. End date - Always "999912" (hardcoded)
    3. HS8_Code - 8-digit HS code
    4. HS8_Unit_of_Measure_Code - alternate_unit_1, defaults to "NMB" if empty
    5. HS8_Edesc - English description (full_description)
    6. HS8_Fdesc - French description (always empty)

    Expected output columns (US format):
    1. valid_from - Date from XML formatted as d/mm/yyyy
    2. valid_to - Date from XML formatted as d/mm/yyyy, defaults to "12/30/9999" if empty
    3. hs - 8-digit HS code
    4. UOM - alternate_unit_1
    5. full_description - English description

    Args:
        nom_df: Processed NOM dataframe with full_description and hs_flag
        txt_df: Optional TXT dataframe (not used)
        config: Configuration object

    Returns:
        DataFrame with country-specific columns for 8-digit HS codes only
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
    # Note: Output format is completely different between countries:
    # - CA: 6 columns with HS8_Code, HS8_Unit_of_Measure_Code, HS8_Edesc, HS8_Fdesc, Start date, End date
    # - US: 5 columns with hs, UOM, full_description, valid_from, valid_to

    if config.country.upper() == 'CA':
        # Canada: Use config year for dates (matches VBA M code)
        start_date_value = f"{config.year}01"
        end_date_value = "999912"
        logger.info(f"CA format: Using Start date={start_date_value}, End date={end_date_value}")

        output_df = pd.DataFrame({
            'Start date': start_date_value,
            'End date': end_date_value,
            'HS8_Code': filtered_nom['number'].fillna('').values,
            'HS8_Unit_of_Measure_Code': filtered_nom['alternate_unit_1'].fillna('NMB').values,
            'HS8_Edesc': filtered_nom['full_description'].fillna('').values,
            'HS8_Fdesc': '',  # Always empty for Export HS format
        })

        # Sort by HS8_Code
        output_df = output_df.sort_values('HS8_Code').reset_index(drop=True)
    else:
        # US: Different column names and format (matches VBA M code)
        logger.info(f"US format: Converting dates to m/d/yyyy format")

        # Convert dates to m/d/yyyy format (without leading zeros)
        valid_from_dates = pd.to_datetime(filtered_nom['valid_from'], errors='coerce')
        valid_from_formatted = valid_from_dates.apply(
            lambda x: f"{x.month}/{x.day}/{x.year}" if pd.notna(x) else ''
        )

        # valid_to defaults to 12/30/9999 if empty
        valid_to_dates = pd.to_datetime(filtered_nom['valid_to'], errors='coerce')
        valid_to_formatted = valid_to_dates.apply(
            lambda x: f"{x.month}/{x.day}/{x.year}" if pd.notna(x) else '12/30/9999'
        )

        output_df = pd.DataFrame({
            'valid_from': valid_from_formatted,
            'valid_to': valid_to_formatted,
            'hs': filtered_nom['number'].fillna('').values,
            'UOM': filtered_nom['alternate_unit_1'].fillna('').values,
            'full_description': filtered_nom['full_description'].fillna('').values,
        })

        # Sort by hs code
        output_df = output_df.sort_values('hs').reset_index(drop=True)

    logger.info(f"Generated {len(output_df)} Export HS records (8-digit only)")

    return output_df
