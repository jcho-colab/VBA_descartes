
import os
import logging
from src.config import ConfigLoader
import openpyxl

# Setup logging
logging.basicConfig(level=logging.INFO)

def debug_conf():
    base_dir = r"d:\VS_project\VBA Descartes"
    excel_path = os.path.join(base_dir, "HS_IMP_v6.3.xlsm")
    
    print(f"Loading config from {excel_path}...")
    try:
        config_loader = ConfigLoader(excel_path)
        
        # Debug: List all tables in Config sheet before loading
        # Need to load wb first manually or let loader do it
        config_loader.wb = openpyxl.load_workbook(config_loader.excel_path, data_only=True)
        ws_config = config_loader.wb["Config"]
        print(f"\nTables in Config sheet: {list(ws_config.tables.keys())}")
        
        # Now load config
        config = config_loader.load(country_override="NZ")
        
        print("\n--- Config Debug (NZ Override) ---")
        print(f"Country: {config.country}")
        print(f"Year: {config.year}")
        print(f"MinChapter: {config.min_chapter}")
        print(f"MaxCSV: {config.max_csv}") # Corrected attribute
        print(f"ZD14Date: {config.zd14_date}")
        
        print(f"\nRateType Keys: {list(config.rate_type_defs.columns)}")
        print(f"RateType Table Size: {len(config.rate_type_defs)}")
        
        if not config.rate_type_defs.empty:
            print("RateType Table First 5 rows:")
            print(config.rate_type_defs.head().to_string())
            
            active_groups = []
            for _, row in config.rate_type_defs.iterrows():
                # Check column names case-insensitively or standard
                # In config.py we read table. usually proper headers.
                # Assuming 'Descartes CG' and 'Comment'
                comment = str(row.get("Comment", "")).lower()
                cg = row.get("Descartes CG", "UNKNOWN")
                if comment != "remove":
                    active_groups.append(cg)
            print(f"\nCalculated Active Groups ({len(active_groups)}): {active_groups}")
        else:
            print("RateType Table is Empty!")
            
        print(f"\nUOM Dict size: {len(config.uom_dict)}")
        if config.uom_dict:
            print(f"Sample UOM: {list(config.uom_dict.items())[0]}")
        
    except Exception as e:
        print(f"Error loading config: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_conf()
