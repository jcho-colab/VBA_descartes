import pandas as pd
import logging
from typing import Optional
from .config import AppConfig

logger = logging.getLogger(__name__)

def generate_export_hs(nom_df: pd.DataFrame, txt_df: Optional[pd.DataFrame], config: AppConfig) -> pd.DataFrame:
    """
    Generate Export HS output format (similar to ExpHSCA/ExpHSUS from VBA).

    This is simpler than the ZD14 import format - it focuses on export HS codes
    with their descriptions and text references.

    Args:
        nom_df: Processed NOM dataframe with full_description
        txt_df: Optional TXT dataframe with text elements
        config: Configuration object

    Returns:
        DataFrame with export HS structure
    """
    logger.info(f"Generating Export HS output for {config.country}")

    filtered_nom = nom_df[nom_df['hs_flag'] == '01-active'].copy()
    logger.info(f"Active NOM records: {len(filtered_nom)}")

    output_data = []

    for _, row in filtered_nom.iterrows():
        hs_code = row.get('number', '')
        level_id = row.get('level_id', '')
        official_desc = row.get('official_description', '')
        full_desc = row.get('full_description', official_desc)
        valid_from = row.get('valid_from', '')
        valid_to = row.get('valid_to', '')

        alt_unit_1 = row.get('alternate_unit_1', '')
        alt_unit_2 = row.get('alternate_unit_2', '')
        alt_unit_3 = row.get('alternate_unit_3', '')

        text_ref = ''
        if txt_df is not None and not txt_df.empty:
            text_matches = row.get('texts', {})
            if isinstance(text_matches, dict):
                text_ref_list = text_matches.get('description_reference', {})
                if isinstance(text_ref_list, dict):
                    text_ref = text_ref_list.get('text_element_id', '')

        output_data.append({
            'HS_Code': hs_code,
            'Level': level_id,
            'Description': full_desc,
            'Official_Description': official_desc,
            'Valid_From': valid_from,
            'Valid_To': valid_to,
            'Alt_Unit_1': alt_unit_1,
            'Alt_Unit_2': alt_unit_2,
            'Alt_Unit_3': alt_unit_3,
            'Text_Reference': text_ref,
            'Country': config.country,
            'Year': config.year
        })

    result_df = pd.DataFrame(output_data)
    logger.info(f"Generated {len(result_df)} Export HS records")

    return result_df
