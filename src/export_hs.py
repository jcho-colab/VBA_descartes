import pandas as pd
import logging
from typing import Optional
from .config import AppConfig

logger = logging.getLogger(__name__)

def generate_export_hs(nom_df: pd.DataFrame, txt_df: Optional[pd.DataFrame], config: AppConfig) -> pd.DataFrame:
    """
    Generate Export HS output format for ExpHSCA/ExpHSUS.

    The VBA QueryOutput creates a query table that:
    - Filters for ONLY 8-digit HS codes (level_id = 40)
    - Filters for active records only (hs_flag = '01-active')
    - Outputs 6 specific columns

    Expected output columns:
    1. Start date (valid_from)
    2. End date (valid_to)
    3. HS8_Code (8-digit HS code)
    4. HS8_Unit_of_Measure_Code (alternate_unit_1)
    5. HS8_Edesc (English description - full_description)
    6. HS8_Fdesc (French description - official_description or empty)

    Args:
        nom_df: Processed NOM dataframe with full_description and hs_flag
        txt_df: Optional TXT dataframe (not used)
        config: Configuration object

    Returns:
        DataFrame with 6 columns for 8-digit HS codes only
    """
    logger.info(f"Generating Export HS output for {config.country}")

    # Filter for active records AND 8-digit codes only (level_id = 40)
    filtered_nom = nom_df[
        (nom_df['hs_flag'] == '01-active') &
        (nom_df['level_id'].astype(str) == '40')
    ].copy()

    logger.info(f"Active 8-digit HS records: {len(filtered_nom)}")

    # Create output with exact column names expected
    output_df = pd.DataFrame({
        'Start date': filtered_nom['valid_from'].fillna('').values,
        'End date': filtered_nom['valid_to'].fillna('').values,
        'HS8_Code': filtered_nom['number'].fillna('').values,
        'HS8_Unit_of_Measure_Code': filtered_nom['alternate_unit_1'].fillna('').values,
        'HS8_Edesc': filtered_nom['full_description'].fillna('').values,
        'HS8_Fdesc': filtered_nom['official_description'].fillna('').values,  # French desc or can be empty
    })

    # Sort by HS8_Code
    output_df = output_df.sort_values('HS8_Code').reset_index(drop=True)

    logger.info(f"Generated {len(output_df)} Export HS records (8-digit only)")

    return output_df
