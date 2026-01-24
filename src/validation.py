import pandas as pd
import logging
from typing import List, Tuple, Set
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


def detect_new_country_groups(dtr_df: pd.DataFrame, config: AppConfig) -> Set[str]:
    """
    Detects country groups in DTR data that are not in the config file.
    Returns set of new country group codes with their duty_rate_type.
    """
    new_groups = set()
    
    if 'country_group' not in dtr_df.columns:
        return new_groups
    
    # Get unique country_group + duty_rate_type combinations from XML
    if 'duty_rate_type' in dtr_df.columns:
        xml_combinations = dtr_df[['country_group', 'duty_rate_type']].dropna().drop_duplicates()
    else:
        return new_groups
    
    # Get all known country groups from config (extract just the country_group part)
    known_groups = set()
    for cg in config.all_country_group_list:
        parts = str(cg).split()
        known_groups.add(parts[0] if parts else str(cg))
    
    # Find groups in XML not in config
    for _, row in xml_combinations.iterrows():
        cg_str = str(row['country_group'])
        if cg_str not in known_groups:
            # Include both country_group and duty_rate_type
            full_cg = f"{cg_str} {row['duty_rate_type']}"
            new_groups.add(full_cg)
    
    if new_groups:
        logger.warning(f"Found {len(new_groups)} new country groups not in config: {new_groups}")
    
    return new_groups


def validate_config(dtr_df: pd.DataFrame, nom_df: pd.DataFrame, config: AppConfig) -> Tuple[bool, dict]:
    """
    Validates that imported data matches configuration.
    Returns (is_valid, dict_of_missing_items)
    """
    logger.info("Validating configuration...")
    
    missing_items = {
        'country_groups': [],  # Now contains "country_group duty_rate_type" format
        'uoms': []
    }
    
    # Validate country groups in DTR - now includes duty_rate_type
    if 'country_group' in dtr_df.columns and 'duty_rate_type' in dtr_df.columns:
        # Get unique combinations from XML
        xml_combinations = dtr_df[['country_group', 'duty_rate_type']].dropna().drop_duplicates()
        
        # Get known country groups (just the first part before space)
        known_groups = set()
        for cg in config.all_country_group_list:
            parts = str(cg).split()
            known_groups.add(parts[0] if parts else str(cg))
        
        # Find new country groups and include their duty_rate_type
        for _, row in xml_combinations.iterrows():
            cg_str = str(row['country_group'])
            if cg_str not in known_groups:
                # Format as "country_group duty_rate_type" for easy copy to config
                full_cg = f"{cg_str} {row['duty_rate_type']}"
                if full_cg not in missing_items['country_groups']:
                    missing_items['country_groups'].append(full_cg)
                    logger.info(f"Found new country group in XML not in config: {full_cg}")
    
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
                logger.info(f"Found UOM in XML not in config (will use as-is): {uom}")
    
    # Log summary
    if missing_items['country_groups']:
        logger.warning(f"BLOCKING: {len(missing_items['country_groups'])} new country groups require config update")
    
    if missing_items['uoms']:
        logger.info(f"Note: {len(missing_items['uoms'])} UOMs from XML not in config table (will be used as-is)")
    
    # Return False if there are new country groups (blocking)
    is_valid = len(missing_items['country_groups']) == 0
    return is_valid, missing_items
