#!/usr/bin/env python3
"""
Verification script to test the FTA tariff processing system.
Compares Python output with VBA-generated reference output.
"""

import os
import sys
import pandas as pd
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def compare_csv_files(python_file: str, vba_file: str) -> dict:
    """
    Compare two CSV files and return comparison results.
    """
    results = {
        'match': False,
        'python_rows': 0,
        'vba_rows': 0,
        'differences': []
    }
    
    try:
        # Read both files
        python_df = pd.read_csv(python_file, sep=';', encoding='utf-8-sig')
        vba_df = pd.read_csv(vba_file, sep=';', encoding='utf-8-sig')
        
        results['python_rows'] = len(python_df)
        results['vba_rows'] = len(vba_df)
        
        # Check row counts
        if len(python_df) != len(vba_df):
            results['differences'].append(f"Row count mismatch: Python={len(python_df)}, VBA={len(vba_df)}")
        
        # Check column counts
        if len(python_df.columns) != len(vba_df.columns):
            results['differences'].append(f"Column count mismatch: Python={len(python_df.columns)}, VBA={len(vba_df.columns)}")
        
        # Check if dataframes are equal
        if len(python_df) == len(vba_df) and len(python_df.columns) == len(vba_df.columns):
            # Compare values (allowing for minor floating point differences)
            try:
                pd.testing.assert_frame_equal(
                    python_df, 
                    vba_df, 
                    check_dtype=False,
                    check_exact=False,
                    rtol=0.01  # 1% tolerance for numeric values
                )
                results['match'] = True
            except AssertionError as e:
                results['differences'].append(f"Data mismatch: {str(e)[:200]}")
        
        return results
        
    except Exception as e:
        results['differences'].append(f"Error comparing files: {str(e)}")
        return results

def verify_outputs():
    """
    Main verification function.
    """
    logger.info("="*80)
    logger.info("FTA Tariff Processing System - Verification")
    logger.info("="*80)
    
    python_dir = Path("/app/output_generated")
    vba_dir = Path("/app/output CSV")
    
    if not python_dir.exists():
        logger.error(f"Python output directory not found: {python_dir}")
        logger.error("Please run the processing pipeline first!")
        return False
    
    if not vba_dir.exists():
        logger.warning(f"VBA reference directory not found: {vba_dir}")
        logger.warning("Skipping comparison with reference output")
        
        # Just list Python outputs
        python_files = sorted(python_dir.glob("*.csv"))
        logger.info(f"\nFound {len(python_files)} Python output file(s):")
        for f in python_files:
            size_kb = f.stat().st_size / 1024
            logger.info(f"  - {f.name} ({size_kb:.1f} KB)")
        return True
    
    # Get list of files to compare
    vba_files = sorted(vba_dir.glob("*.csv"))
    python_files = sorted(python_dir.glob("*.csv"))
    
    logger.info(f"\nVBA Reference Files: {len(vba_files)}")
    logger.info(f"Python Output Files: {len(python_files)}")
    
    if len(python_files) == 0:
        logger.error("No Python output files found!")
        return False
    
    # Compare each file
    all_match = True
    comparisons = []
    
    for vba_file in vba_files:
        # Try to find corresponding Python file
        # VBA: "NZ UPLOAD _ZD14 V1-1.csv"
        # Python might have different version number
        base_name = vba_file.stem.rsplit(' V', 1)[0]  # "NZ UPLOAD _ZD14"
        file_num = vba_file.stem.split('-')[-1]  # "1"
        
        # Find matching Python file
        python_file = None
        for pf in python_files:
            if base_name in pf.stem and f"-{file_num}." in str(pf):
                python_file = pf
                break
        
        if not python_file:
            logger.warning(f"\n⚠️  No matching Python file for: {vba_file.name}")
            all_match = False
            continue
        
        logger.info(f"\n📊 Comparing: {vba_file.name} vs {python_file.name}")
        
        results = compare_csv_files(str(python_file), str(vba_file))
        comparisons.append({
            'vba': vba_file.name,
            'python': python_file.name,
            'results': results
        })
        
        if results['match']:
            logger.info(f"   ✅ MATCH - Files are identical ({results['python_rows']} rows)")
        else:
            logger.error(f"   ❌ MISMATCH")
            logger.error(f"      Python rows: {results['python_rows']}")
            logger.error(f"      VBA rows: {results['vba_rows']}")
            for diff in results['differences']:
                logger.error(f"      - {diff}")
            all_match = False
    
    # Summary
    logger.info("\n" + "="*80)
    if all_match and comparisons:
        logger.info("✅ VERIFICATION PASSED - All outputs match VBA reference!")
    elif comparisons:
        matches = sum(1 for c in comparisons if c['results']['match'])
        logger.warning(f"⚠️  VERIFICATION PARTIAL - {matches}/{len(comparisons)} files match")
    else:
        logger.error("❌ VERIFICATION FAILED - No successful comparisons")
    logger.info("="*80)
    
    return all_match

if __name__ == "__main__":
    success = verify_outputs()
    sys.exit(0 if success else 1)
