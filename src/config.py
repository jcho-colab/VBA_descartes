import pandas as pd
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class AppConfig:
    country: str
    year: str
    min_chapter: int
    max_csv: int
    zd14_date: Any
    rate_type_defs: pd.DataFrame
    uom_dict: Dict[str, str]
    country_list: List[str]
    chapter_list: List[str]
    active_country_group_list: List[str]
    all_country_group_list: List[str]


class ConfigLoader:
    """Configuration loader that reads from JSON files in Configuration_files folder."""
    
    def __init__(self, config_dir: str = "Configuration_files"):
        self.config_dir = config_dir
        
    def load(self, country_override: Optional[str] = None) -> AppConfig:
        logger.info(f"Loading configuration from {self.config_dir}")
        
        # Check if config directory exists
        if not os.path.exists(self.config_dir):
            raise FileNotFoundError(f"Configuration directory not found: {self.config_dir}")
        
        # Load global settings
        global_settings_path = os.path.join(self.config_dir, "global_settings.json")
        if not os.path.exists(global_settings_path):
            raise FileNotFoundError(f"Global settings file not found: {global_settings_path}")
        
        with open(global_settings_path, 'r') as f:
            global_settings = json.load(f)
        
        # Determine country
        if country_override:
            country = country_override.upper()
            logger.info(f"Using Country Override: {country}")
        else:
            country = global_settings.get("default_country", "NZ").upper()
        
        year = str(global_settings.get("year", "2026"))
        min_chapter = int(global_settings.get("min_chapter", 25))
        max_csv = int(global_settings.get("max_csv", 30000))
        zd14_date = global_settings.get("zd14_date")
        
        logger.info(f"Loaded Global Settings: Country={country}, Year={year}, MinChapter={min_chapter}")
        
        # Generate chapter list
        chapter_list = [str(i).zfill(2) for i in range(min_chapter, 100)]
        
        # Load country-specific configuration
        country_config_path = os.path.join(self.config_dir, f"{country.lower()}_config.json")
        if not os.path.exists(country_config_path):
            raise FileNotFoundError(f"Country configuration not found: {country_config_path}")
        
        with open(country_config_path, 'r') as f:
            country_config = json.load(f)
        
        # Parse rate types
        rate_types_data = country_config.get("rate_types", [])
        rate_type_df = pd.DataFrame(rate_types_data) if rate_types_data else pd.DataFrame()
        
        # Parse UOM mappings
        uom_mappings = country_config.get("uom_mappings", [])
        uom_dict = {}
        for mapping in uom_mappings:
            descartes_uom = mapping.get("Descartes UOM")
            sap_uom = mapping.get("SAP UOM")
            if descartes_uom is not None and sap_uom is not None:
                uom_dict[descartes_uom] = sap_uom
        
        # Load Country List (for EU)
        country_list = [country]
        if country == "EU":
            eu_country_list = country_config.get("country_list", [])
            if eu_country_list:
                country_list = [item.get("Country", item) if isinstance(item, dict) else item 
                               for item in eu_country_list]
        
        # Extract active and all country group lists
        active_country_group_list = []
        all_country_group_list = []
        
        if not rate_type_df.empty and "Descartes CG" in rate_type_df.columns:
            for _, row in rate_type_df.iterrows():
                cg_full = row["Descartes CG"]
                if pd.notna(cg_full):
                    cg_parts = str(cg_full).split()
                    cg = cg_parts[0] if cg_parts else str(cg_full)
                    
                    all_country_group_list.append(str(cg_full))
                    
                    if cg not in all_country_group_list:
                        all_country_group_list.append(cg)
                    
                    comment = str(row.get("Comment", "")).lower()
                    if "remove" not in comment:
                        active_country_group_list.append(str(cg_full))
                        if cg not in active_country_group_list:
                            active_country_group_list.append(cg)

        return AppConfig(
            country=country,
            year=year,
            min_chapter=min_chapter,
            max_csv=max_csv,
            zd14_date=zd14_date,
            rate_type_defs=rate_type_df,
            uom_dict=uom_dict,
            country_list=country_list,
            chapter_list=chapter_list,
            active_country_group_list=active_country_group_list,
            all_country_group_list=all_country_group_list
        )
    
    def get_available_countries(self) -> List[str]:
        """Returns list of available countries based on config files."""
        countries = []
        if os.path.exists(self.config_dir):
            for filename in os.listdir(self.config_dir):
                if filename.endswith("_config.json") and filename != "global_settings.json":
                    country = filename.replace("_config.json", "").upper()
                    countries.append(country)
        return sorted(countries)
