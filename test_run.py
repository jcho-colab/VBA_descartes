#!/usr/bin/env python3
"""
Test script to run the processing pipeline and compare with VBA output.
"""

import os
import sys
import glob
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, '/app')

from src.config import ConfigLoader
from src.ingest import parse_xml_to_df
from src.process import cleanse_hs, filter_active_country_groups, filter_by_chapter, flag_hs, build_descriptions
from src.export import generate_zd14, export_csv_split
from src.validation import validate_rates, validate_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("="*80)
    logger.info("FTA Tariff Processing - Test Run")
    logger.info("="*80)
    
    try:
        # 1. Load Configuration
        logger.info("\n[1/6] Loading Configuration...")
        excel_path = "/app/HS_IMP_v6.3.xlsm"
        
        if not os.path.exists(excel_path):
            logger.error(f"Configuration file not found: {excel_path}")
            return False
        
        loader = ConfigLoader(excel_path)
        config = loader.load(country_override="NZ")  # Force NZ for testing
        
        logger.info(f"✅ Config loaded: {config.country} ({config.year})")
        logger.info(f"   Min Chapter: {config.min_chapter}")
        logger.info(f"   Active Country Groups: {len(config.active_country_group_list)}")
        
        # 2. Ingest XML Files
        logger.info("\n[2/6] Ingesting XML Files...")
        
        input_dir = "/app/input XML"
        dtr_files = sorted(glob.glob(os.path.join(input_dir, "*DTR*.xml")))
        nom_files = sorted(glob.glob(os.path.join(input_dir, "*NOM*.xml")))
        txt_files = sorted(glob.glob(os.path.join(input_dir, "*TXT*.xml")))
        
        logger.info(f"   Found {len(dtr_files)} DTR files")
        logger.info(f"   Found {len(nom_files)} NOM files")
        logger.info(f"   Found {len(txt_files)} TXT files")
        
        dtr_df = parse_xml_to_df(dtr_files, "DTR")
        nom_df = parse_xml_to_df(nom_files, "NOM")
        
        logger.info(f"✅ Loaded: DTR={len(dtr_df)} rows, NOM={len(nom_df)} rows")
        
        # 3. Validation
        logger.info("\n[3/6] Validating Data...")
        
        # Create concat_cg_drt for validation
        if 'country_group' in dtr_df.columns and 'duty_rate_type' in dtr_df.columns:
            dtr_df['concat_cg_drt'] = dtr_df['country_group'].fillna('') + " " + dtr_df['duty_rate_type'].fillna('')
        
        # Rate validation
        rate_valid, invalid_hs = validate_rates(dtr_df, config)
        if not rate_valid:
            logger.warning(f"⚠️  {len(invalid_hs)} HS codes missing rate text (first 5): {invalid_hs[:5]}")
        else:
            logger.info("✅ All DTR records have valid rates")
        
        # Config validation
        config_valid, missing_items = validate_config(dtr_df, nom_df, config)
        if not config_valid:
            if missing_items['country_groups']:
                logger.warning(f"⚠️  Unmapped country groups: {len(missing_items['country_groups'])}")
            if missing_items['uoms']:
                logger.warning(f"⚠️  Unmapped UOMs: {len(missing_items['uoms'])}")
        else:
            logger.info("✅ Configuration validated successfully")
        
        # 4. Process DTR Data
        logger.info("\n[4/6] Processing DTR Data...")
        
        dtr_df = cleanse_hs(dtr_df, 'hs')
        logger.info(f"   ✓ Cleansed HS codes")
        
        dtr_df = filter_by_chapter(dtr_df, config)
        logger.info(f"   ✓ Filtered by chapter ({len(dtr_df)} rows)")
        
        dtr_df = filter_active_country_groups(dtr_df, config)
        logger.info(f"   ✓ Filtered country groups ({len(dtr_df)} rows)")
        
        dtr_df = flag_hs(dtr_df, config, "DTR")
        logger.info(f"   ✓ Flagged HS codes")
        
        # Filter active only
        dtr_active = dtr_df[dtr_df['hs_flag'] == '01-active'].copy()
        logger.info(f"✅ Active DTR records: {len(dtr_active)}/{len(dtr_df)}")
        
        # 5. Process NOM Data
        logger.info("\n[5/6] Processing NOM Data...")
        
        nom_df = cleanse_hs(nom_df, 'number')
        logger.info(f"   ✓ Cleansed NOM numbers")
        
        nom_df = flag_hs(nom_df, config, "NOM")
        logger.info(f"   ✓ Flagged NOM records")
        
        nom_df = build_descriptions(nom_df)
        logger.info(f"✅ Processed NOM: {len(nom_df)} records with descriptions")
        
        # 6. Generate ZD14 and Export
        logger.info("\n[6/6] Generating ZD14 Output...")
        
        zd14 = generate_zd14(dtr_active, nom_df, config)
        logger.info(f"✅ Generated ZD14: {len(zd14)} rows, {len(zd14.columns)} columns")
        
        # Export
        output_dir = "/app/output_generated"
        os.makedirs(output_dir, exist_ok=True)
        
        prefix = f"{config.country} UPLOAD _ZD14"
        exported_files = export_csv_split(zd14, output_dir, prefix, config.max_csv)
        
        logger.info(f"✅ Exported {len(exported_files)} file(s):")
        for f in exported_files:
            size_kb = os.path.getsize(f) / 1024
            logger.info(f"   - {os.path.basename(f)} ({size_kb:.1f} KB)")
        
        logger.info("\n" + "="*80)
        logger.info("✅ Processing Complete!")
        logger.info("="*80)
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Error occurred: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
