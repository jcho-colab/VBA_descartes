import openpyxl
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Any
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

class ConfigLoader:
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.wb = None
        
    def load(self, country_override: str = None) -> AppConfig:
        logger.info(f"Loading configuration from {self.excel_path}")
        self.wb = openpyxl.load_workbook(self.excel_path, data_only=True)
        
        # Load Menu settings
        menu_sheet = self.wb["Menu"]
        
        if country_override:
            country = country_override
            logger.info(f"Using Country Override: {country}")
        else:
            country = self._get_named_range_value("Country")
            
        year = str(self._get_named_range_value("Year")) 
        min_chapter = int(self._get_named_range_value("MinChapter"))
        max_csv = int(self._get_named_range_value("MaxCSV"))
        zd14_date = self._get_named_range_value("ZD14Date")
        
        logger.info(f"Loaded Global Settings: Country={country}, Year={year}")
        
        # Load Config tables
        config_sheet = self.wb["Config"]
        
        # Helper to find table case-insensitively
        def find_table(base_name):
            # Try exact
            if base_name in config_sheet.tables:
                return base_name
            # Try lower case prefix (e.g. VNRateType -> vnRateType)
            # Try lower case full (e.g. VNRateType -> vnratetype)
            # Iterate keys
            for key in config_sheet.tables.keys():
                if key.lower() == base_name.lower():
                    return key
            return base_name

        # Load RateType Table
        rate_type_base = f"{country}RateType"
        rate_type_table_name = find_table(rate_type_base)
        rate_type_df = self._read_table(config_sheet, rate_type_table_name)
        
        # Load UOM Table
        uom_base = f"{country}UOM"
        uom_table_name = find_table(uom_base)
        uom_df = self._read_table(config_sheet, uom_table_name)
        
        uom_dict = {}
        if not uom_df.empty and "Descartes UOM" in uom_df.columns and "SAP UOM" in uom_df.columns:
             uom_dict = dict(zip(uom_df["Descartes UOM"], uom_df["SAP UOM"]))

        # Load Country List (for EU)
        country_list = [country]
        if country == "EU":
            cl_base = f"{country}CountryList"
            country_list_table_name = find_table(cl_base)
            cl_df = self._read_table(config_sheet, country_list_table_name)
            if not cl_df.empty:
                country_list = cl_df.iloc[:, 0].tolist()

        return AppConfig(
            country=country,
            year=year,
            min_chapter=min_chapter,
            max_csv=max_csv,
            zd14_date=zd14_date,
            rate_type_defs=rate_type_df,
            uom_dict=uom_dict,
            country_list=country_list
        )

    def _get_named_range_value(self, name: str) -> Any:
        """Retrieves the value of a named range."""
        try:
            defined_name = self.wb.defined_names[name]
            # This returns a list of destinations, usually just one
            for title, coord in defined_name.destinations:
                ws = self.wb[title]
                return ws[coord].value
            
            # If standard lookup fails, try refined parsing (openpyxl can be tricky with some named ranges)
            # Sometimes dest is None but encoded in value
            return None
        except Exception as e:
            logger.warning(f"Could not read named range '{name}': {e}")
            return None

    def _read_table(self, sheet, table_name: str) -> pd.DataFrame:
        """Reads an Excel table (ListObject) into a DataFrame."""
        try:
            # openpyxl stores tables in sheet.tables
            if table_name not in sheet.tables:
                logger.warning(f"Table '{table_name}' not found in sheet '{sheet.title}'")
                return pd.DataFrame()

            tbl = sheet.tables[table_name]
            ref = tbl.ref # e.g. "A1:C5"
            
            data = sheet[ref]
            rows = [[cell.value for cell in row] for row in data]
            
            if not rows:
                return pd.DataFrame()

            header = rows[0]
            body = rows[1:]
            
            return pd.DataFrame(body, columns=header)
        except Exception as e:
            logger.error(f"Error reading table '{table_name}': {e}")
            return pd.DataFrame()
