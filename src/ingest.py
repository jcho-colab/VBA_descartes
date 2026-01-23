import pandas as pd
from lxml import etree
import logging
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

def parse_xml_to_df(file_paths: List[str], doc_type: str) -> pd.DataFrame:
    """
    Parses a list of XML files of a specific type (DTR, NOM, TXT) into a single DataFrame.
    """
    all_data = []
    
    for file_path in file_paths:
        logger.info(f"Parsing {os.path.basename(file_path)} as {doc_type}")
        try:
            tree = etree.parse(file_path)
            root = tree.getroot()
            
            if doc_type == "DTR":
                # Deep parsing for DTR
                # Root -> body -> duty_rate_entity (attrs) -> country_group (attr id) -> rate -> constraint -> *Rate (attrs + desc)
                # Also preference_note
                
                entities = root.findall(".//{*}duty_rate_entity")
                if not entities: entities = root.findall(".//duty_rate_entity")
                
                for ent in entities:
                    # Base Entity Types
                    base_row = {
                        "hs": ent.get("hs_id"),
                        "duty_rate_type": ent.get("duty_rate_type"),
                        "valid_from": ent.get("valid_from"),
                        "valid_to": ent.get("valid_to"),
                        "deleted": ent.get("deleted")
                    }
                    
                    # Country Groups (usually 1 per entity in these XMLs, but could be multiple?)
                    # The XML schema suggests entities might have multiple CGS? 
                    # Sample shows: <duty_rate_entity ...> <country_group ...>
                    cgs = ent.findall(".//{*}country_group")
                    if not cgs: cgs = ent.findall(".//country_group")
                    
                    for cg in cgs:
                        row = base_row.copy()
                        row["country_group"] = cg.get("id")
                        
                        # Rates
                        # Look for specific rate types under rate/constraint
                        # Handle multiple constraints? unique rate per type usually.
                        
                        # Helper to extract rate info
                        def extract_rate(rate_node, prefix):
                            # Percentage/Amount
                            if prefix == "adValoremRate":
                                row[f"{prefix}_percentage"] = rate_node.get("percentage")
                            elif prefix == "specificRate":
                                row[f"{prefix}_ratePerUOM"] = rate_node.get("ratePerUOM") # verify XML attr name
                                # Unit?
                            elif prefix == "compoundRate":
                                row[f"{prefix}_percentage"] = rate_node.get("percentage")
                                # compound might have ratePerUOM too?
                                
                            # Description
                            desc = rate_node.find(".//{*}description")
                            if desc is None: desc = rate_node.find(".//description")
                            if desc is not None:
                                row[f"{prefix}_text"] = desc.get("text")
                        
                        # Check for each rate type
                        for rtype in ["adValoremRate", "specificRate", "compoundRate", "freeRate", "complexRate"]:
                             # Search recursively in this CG
                             rnode = cg.find(f".//{{*}}{rtype}")
                             if rnode is None: rnode = cg.find(f".//{rtype}")
                             
                             if rnode is not None:
                                 extract_rate(rnode, rtype)
                                 
                        # Preference Note (Regulation)
                        pref = cg.find(".//{*}preference_note")
                        if pref is None: pref = cg.find(".//preference_note")
                        
                        if pref is not None:
                            note = pref.find(".//{*}note")
                            if note is None: note = pref.find(".//note")
                            if note is not None:
                                row["regulation"] = note.get("text")
                                
                        all_data.append(row)
                        
            elif doc_type == "NOM":
                # Path: body -> number_data
                nodes = root.findall(".//{*}number_data")
                if not nodes: nodes = root.findall(".//number_data")
                
                for node in nodes:
                    row = {}
                    # Direct children + attributes if any? 
                    # Valid XML for NOM has tags like <number>, <id> as children.
                    
                    for child in node:
                        tag = etree.QName(child).localname
                        if tag == "texts":
                            # Handle nested official_description
                            off_desc = child.find(".//{*}official_description")
                            if off_desc is None: off_desc = child.find(".//official_description")
                            
                            if off_desc is not None:
                                txt_node = off_desc.find(".//{*}text")
                                if txt_node is None: txt_node = off_desc.find(".//text")
                                if txt_node is not None:
                                    row["official_description"] = txt_node.text
                        else:
                            row[tag] = child.text
                    all_data.append(row)
                    
            elif doc_type == "TXT":
                # Path: body -> texts -> text_element -> text
                # Also capture text_element_id from direct child
                
                nodes = root.findall(".//{*}texts")
                if not nodes: nodes = root.findall(".//texts")
                
                for node in nodes:
                    row = {}
                    for child in node:
                        tag = etree.QName(child).localname
                        if tag == "text_element":
                            txt_node = child.find(".//{*}text")
                            if txt_node is None: txt_node = child.find(".//text")
                            if txt_node is not None:
                                row["text_content"] = txt_node.text
                        else:
                            row[tag] = child.text
                    all_data.append(row)

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            
    df = pd.DataFrame(all_data)
    logger.info(f"Loaded {len(df)} rows for {doc_type}")
    return df
