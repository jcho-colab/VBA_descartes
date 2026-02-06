import pandas as pd
import logging
from typing import Optional
from .config import AppConfig

logger = logging.getLogger(__name__)

def generate_export_hs(nom_df: pd.DataFrame, txt_df: Optional[pd.DataFrame], config: AppConfig) -> pd.DataFrame:
    """
    Generate Export HS output format (similar to ExpHSCA/ExpHSUS from VBA).

    The VBA QueryOutput function creates a query table that pulls specific columns
    from the processed NOM table, filtering for active records only.

    This replicates that query table output by selecting:
    - Only active records (hs_flag = '01-active')
    - Key columns: HS code, full description, dates, units, level

    Args:
        nom_df: Processed NOM dataframe with full_description and hs_flag
        txt_df: Optional TXT dataframe (not used in query table, kept for compatibility)
        config: Configuration object

    Returns:
        DataFrame with export HS structure matching VBA query table output
    """
    logger.info(f"Generating Export HS output for {config.country}")

    # Filter for active records only (replicates query table WHERE clause)
    filtered_nom = nom_df[nom_df['hs_flag'] == '01-active'].copy()
    logger.info(f"Active NOM records: {len(filtered_nom)}")

    # Select and rename columns to match expected output
    # The query table in VBA selects specific columns from TableNOM
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

    # Sort by HS code (matching VBA final sort)
    output_df = output_df.sort_values('hs').reset_index(drop=True)

    logger.info(f"Generated {len(output_df)} Export HS records")

    return output_df
