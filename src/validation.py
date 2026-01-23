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
    Now supports dynamic country group mapping from XML data.
    Returns (is_valid, dict_of_missing_items)
    """
    logger.info("Validating configuration...")
    
    missing_items = {
        'country_groups': [],
        'uoms': []
    }
    
    # Validate country groups in DTR - now extract from actual country_group column
    if 'country_group' in dtr_df.columns and config.all_country_group_list:
        unique_cgs = dtr_df['country_group'].dropna().unique().tolist()
        
        # Only warn about unmapped groups, don't fail validation
        # This allows dynamic mapping from XML files
        for cg in unique_cgs:
            if cg not in config.all_country_group_list:
                missing_items['country_groups'].append(cg)
                logger.info(f"Found country group in XML not in config (will be processed): {cg}")
    
    # Validate UOMs in NOM - also allow dynamic mapping
    if not nom_df.empty:
        uom_columns = ['alternate_unit_1', 'alternate_unit_2', 'alternate_unit_3']
        unique_uoms = set()
        
        for col in uom_columns:
            if col in nom_df.columns:
                unique_uoms.update(nom_df[col].dropna().unique().tolist())
        
        for uom in unique_uoms:
            if uom and uom not in config.uom_dict.keys():
                missing_items['uoms'].append(uom)
                logger.info(f"Found UOM in XML not in config (will use as-is): {uom}")
    
    # Log summary
    if missing_items['country_groups']:
        logger.info(f"Note: {len(missing_items['country_groups'])} country groups from XML not in config table (will be processed)")
    
    if missing_items['uoms']:
        logger.info(f"Note: {len(missing_items['uoms'])} UOMs from XML not in config table (will be used as-is)")
    
    # Return True - validation is informational only, not blocking
    # This allows processing of data with country groups/UOMs not in config
    return True, missing_items
