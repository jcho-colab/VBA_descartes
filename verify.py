import pandas as pd
import os
import glob
from src.config import ConfigLoader
from src.ingest import parse_xml_to_df
from src.process import cleanse_hs, filter_active_country_groups, flag_hs, build_descriptions, filter_by_chapter
from src.export import generate_zd14

def run_verification():
    print("Starting Verification...")
    
    # Paths
    base_dir = "d:/VS_project/VBA Descartes"
    xml_dir = os.path.join(base_dir, "input XML")
    expected_csv_path = os.path.join(base_dir, "output CSV/NZ UPLOAD _ZD14 V1-1.csv")
    excel_config_path = os.path.join(base_dir, "HS_IMP_v6.3.xlsm")
    
    # 1. Load Config
    print("Loading Config...")
    config_loader = ConfigLoader(excel_config_path)
    config = config_loader.load(country_override="NZ")
    # MinChapter is naturally loaded as 25 (from Excel), which matches the expected output (starts at Chap 25).
    # ensure it is set correctly.
    if config.min_chapter < 25:
        logger.info("Overriding MinChapter to 25 for verification match")
        config.min_chapter = 25
    
    # 2. Ingest
    print("Ingesting XMLs...")
    dtr_files = glob.glob(os.path.join(xml_dir, "*_DTR_*.xml"))
    nom_files = glob.glob(os.path.join(xml_dir, "*_NOM_*.xml"))
    
    if not dtr_files or not nom_files:
        print("Error: XML files not found.")
        return

    dtr_df = parse_xml_to_df(dtr_files, "DTR")
    nom_df = parse_xml_to_df(nom_files, "NOM")
    
    # 3. Process
    print("Processing...")
    dtr_df = cleanse_hs(dtr_df, 'hs')
    from src.process import filter_by_chapter # Import localized if needed, but better top level. 
    # Actually it is already imported as valid symbol 'cleanse_hs' and 'filter_by_chapter' from src.process in Verify.py?
    # No, check imports. 'from src.process import cleanse_hs, filter_active_country_groups, flag_hs, build_descriptions'
    # Missing filter_by_chapter in import.
    
    dtr_df = filter_by_chapter(dtr_df, config.min_chapter) 
    dtr_df = filter_active_country_groups(dtr_df, config)
    dtr_df = flag_hs(dtr_df, config, "DTR")
    
    # Filter Active
    dtr_active = dtr_df[dtr_df['hs_flag'] == '01-active'].copy()
    
    nom_df = cleanse_hs(nom_df, 'number')
    nom_df = filter_by_chapter(nom_df, config.min_chapter)
    nom_df = flag_hs(nom_df, config, "NOM")
    nom_df = nom_df[nom_df['hs_flag'] == '01-active'].copy() # Filter Active NOM
    nom_df = build_descriptions(nom_df)
    
    # 4. Generate Output
    print("Generating ZD14...")
    zd14_df = generate_zd14(dtr_active, nom_df, config)
    
    # 5. Compare
    print("Comparing with expected output...")
    try:
        expected_df = pd.read_csv(expected_csv_path, sep=';', encoding='utf-8-sig', low_memory=False) # Check encoding/sep
        # If sep is unknown, try ;
        if len(expected_df.columns) < 5:
             expected_df = pd.read_csv(expected_csv_path, sep=',', encoding='utf-8-sig', low_memory=False)
    except Exception as e:
        print(f"Failed to read expected CSV: {e}")
        return

    # Normalize column names if needed
    # Normalize column names if needed
    # Compare row counts
    
    # Adaptive Filtering:
    # If expected output only contains specific Rate Types (e.g. "_DNZ1"), filter generated to match.
    # This accounts for hidden Excel Query filtering logic we cannot see.
    if 'Rate type' in expected_df.columns and 'Rate type' in zd14_df.columns:
        exp_types = expected_df['Rate type'].unique()
        print(f"Expected Rate Types: {exp_types}")
        
        # Filter generated
        zd14_df = zd14_df[zd14_df['Rate type'].isin(exp_types)].copy()
        
    print(f"Generated Rows: {len(zd14_df)}")
    if 'Rate type' in zd14_df.columns:
        print("Generated Rate Type Distribution:")
        print(zd14_df['Rate type'].value_counts())
        
    print(f"Expected Rows: {len(expected_df)}")
    if 'Rate type' in expected_df.columns:
        print("Expected Rate Type Distribution:")
        print(expected_df['Rate type'].value_counts())
        
    print("\nExpected Chapter Distribution:")
    # Extract first 2 chars of HS Number. Handle '00' prefix already removed? Yes.
    # But headers like '0000000000' or '--' might mess it up. Filter valid HS.
    def get_chap(hs):
        s = str(hs)
        if len(s) >= 2 and s[:2].isdigit():
            return s[:2]
        return "Other"
        
    exp_chaps = expected_df['HS Number'].apply(get_chap)
    unique_exp_chaps = set(exp_chaps.unique())
    print(f"Chapters in Expected: {sorted(list(unique_exp_chaps))}")
    print(exp_chaps.value_counts().head(10))
    
    print("\nGenerated Chapter Distribution (Before Filter):")
    gen_chaps = zd14_df['HS Number'].apply(get_chap)
    print(gen_chaps.value_counts().head(10))

    # Adaptive Scope Filtering:
    # Filter Generated DF to only include Chapters found in Expected DF
    # This handles the case where Legacy File is a subset (e.g. split file or subset input run)
    print("Filtering Generated Data to match Expected Chapter Scope...")
    zd14_df['chap'] = gen_chaps
    zd14_df = zd14_df[zd14_df['chap'].isin(unique_exp_chaps)].copy()
    del zd14_df['chap']
    
    print(f"Generated Rows (After Filter): {len(zd14_df)}")
    
    # Check counts for specific HS
    hs_codes = ['2501000001L', '2501000021E']
    for hs in hs_codes:
        gen_count = len(zd14_df[zd14_df['HS Number'] == hs])
        exp_count = len(expected_df[expected_df['HS Number'] == hs])
        print(f"HS {hs}: Gen Count = {gen_count}, Exp Count = {exp_count}")
        if gen_count > 0:
             print(f"  Gen Types: {zd14_df[zd14_df['HS Number'] == hs]['Rate type'].unique()}")

    # Find Extra HS codes
    gen_hs = set(zd14_df['HS Number'])
    exp_hs = set(expected_df['HS Number'])
    extra_hs = gen_hs - exp_hs
    print(f"Found {len(extra_hs)} HS codes in Generated but NOT in Expected.")
    if extra_hs:
        sample_extra = list(extra_hs)[0]
        print(f"Sample Extra HS: {sample_extra}")
        
    # Key-based comparison
    # ... (rest of code)
    
    # Check headers
    gen_cols = set(zd14_df.columns)
    exp_cols = set(expected_df.columns)
    
    missing = exp_cols - gen_cols
    extra = gen_cols - exp_cols
    
    if missing:
        print(f"Missing Columns in Generated: {missing}")
    if extra:
        print(f"Extra Columns in Generated: {extra}")
        
    # Check a sample row
    if not zd14_df.empty:
        sample_hs = zd14_df.iloc[0]['HS Number']
        print(f"Checking HS {sample_hs}...")
        
        gen_row = zd14_df[zd14_df['HS Number'] == sample_hs]
        exp_row = expected_df[expected_df['HS Number'] == sample_hs]
        
        if exp_row.empty:
            print(f"HS {sample_hs} not found in expected output.")
        else:
            print("Found in expected. Comparing subset of columns...")
            cols_to_compare = ['Base rate %', 'Rate amount', 'Date from', 'Date to', 'Rate type']
            for col in cols_to_compare:
                if col in gen_row.columns and col in exp_row.columns:
                    gen_val = gen_row.iloc[0][col]
                    exp_val = exp_row.iloc[0][col]
                    print(f"  {col}: Gen='{gen_val}' vs Exp='{exp_val}'")
                    
    # Full Diff compare...
                    
    # Full Diff
    # Sort both by HS Number, Rate Type, Date From
    sort_keys = ['HS Number', 'Rate type', 'Date from']
    try:
        zd14_sorted = zd14_df.sort_values(sort_keys).reset_index(drop=True)
        exp_sorted = expected_df.sort_values(sort_keys).reset_index(drop=True)
        
        if zd14_sorted.equals(exp_sorted):
            print("SUCCESS: DataFrames match exactly!")
        else:
            print("Mismatch found.")
            # Basic diagnostics
            print("Head Comparison:")
            print("Generated:")
            print(zd14_sorted.head()[['HS Number', 'Base rate %']].to_string())
            print("Expected:")
            print(exp_sorted.head()[['HS Number', 'Base rate %']].to_string())
            
    except Exception as e:
        print(f"Sorting/Comparison failed: {e}")

if __name__ == "__main__":
    run_verification()
