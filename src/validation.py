import pandas as pd
import logging
from typing import List, Tuple
from .config import AppConfig

logger = logging.getLogger(__name__)

def validate_rates(dtr_df: pd.DataFrame, config: AppConfig) -> Tuple[bool, List[str]]:
    """
    Validates that all DTR records have rate text or regulation.
    Returns (is_valid, list_of_invalid_hs)
    """
    logger.info("Validating DTR rates...")
    
    rate_columns = [
        'complexRate_text',
        'compoundRate_text', 
        'specificRate_text',
        'adValoremRate_text',
        'freeRate_text',
        'regulation'
    ]
    
    # Find rows where all rate text columns are empty
    invalid_hs = []
    
    for _, row in dtr_df.iterrows():
        has_rate = False
        for col in rate_columns:
            if col in row and pd.notna(row[col]) and str(row[col]).strip():
                has_rate = True
                break
        
        if not has_rate:
            hs = row.get('hs', 'unknown')
            if hs not in invalid_hs:
                invalid_hs.append(str(hs))
    
    if invalid_hs:
        logger.warning(f"Found {len(invalid_hs)} HS codes without rate text or regulation")
        return False, invalid_hs
    else:
        logger.info("All DTR records have valid rate text or regulation")
        return True, []

def validate_config(dtr_df: pd.DataFrame, nom_df: pd.DataFrame, config: AppConfig) -> Tuple[bool, dict]:
    """
    Validates that imported data matches configuration.
    Returns (is_valid, dict_of_missing_items)
    """
    logger.info("Validating configuration...")
    
    missing_items = {
        'country_groups': [],
        'uoms': []
    }
    
    # Validate country groups in DTR
    if 'concat_cg_drt' in dtr_df.columns and config.all_country_group_list:
        unique_cgs = dtr_df['concat_cg_drt'].dropna().unique().tolist()
        for cg in unique_cgs:
            if cg not in config.all_country_group_list:
                missing_items['country_groups'].append(cg)
    
    # Validate UOMs in NOM
    if not nom_df.empty:
        uom_columns = ['alternate_unit_1', 'alternate_unit_2', 'alternate_unit_3']
        unique_uoms = set()
        
        for col in uom_columns:
            if col in nom_df.columns:
                unique_uoms.update(nom_df[col].dropna().unique().tolist())
        
        for uom in unique_uoms:
            if uom and uom not in config.uom_dict.keys():
                missing_items['uoms'].append(uom)
    
    if missing_items['country_groups']:
        logger.warning(f"Found {len(missing_items['country_groups'])} unmapped country groups")
    
    if missing_items['uoms']:
        logger.warning(f"Found {len(missing_items['uoms'])} unmapped UOMs")
    
    is_valid = not (missing_items['country_groups'] or missing_items['uoms'])
    
    return is_valid, missing_items
