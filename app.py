import streamlit as st
import pandas as pd
import os
import shutil
import tempfile
import logging
from src.config import ConfigLoader
from src.ingest import parse_xml_to_df
from src.process import cleanse_hs, filter_active_country_groups, flag_hs, build_descriptions
from src.export import generate_zd14, export_csv_split

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Excel to Python Migration", layout="wide")

st.title("FTA Tariff Rates Migration")

# 1. Configuration
st.sidebar.header("Configuration")
excel_path = st.sidebar.text_input("Config Excel Path", value="d:/VS_project/VBA Descartes/HS_IMP_v6.3.xlsm")

if st.sidebar.button("Load Config"):
    try:
        loader = ConfigLoader(excel_path)
        config = loader.load()
        st.session_state['config'] = config
        st.success(f"Loaded config for Country: {config.country}, Year: {config.year}")
    except Exception as e:
        st.error(f"Failed to load config: {e}")

if 'config' in st.session_state:
    config = st.session_state['config']
    
    st.header(f"Processing for {config.country}")
    
    # 2. File Upload
    col1, col2, col3 = st.columns(3)
    
    with col1:
        dtr_files = st.file_uploader("Upload DTR XMLs", type="xml", accept_multiple_files=True)
    with col2:
        nom_files = st.file_uploader("Upload NOM XMLs", type="xml", accept_multiple_files=True)
    with col3:
        txt_files = st.file_uploader("Upload TXT XMLs", type="xml", accept_multiple_files=True)
        
    if st.button("Run Migration Process"):
        if not dtr_files or not nom_files: # TXT optional?
            st.error("Please upload at least DTR and NOM files.")
        else:
            status = st.empty()
            progress = st.progress(0)
            
            try:
                # Helper to save uploaded files to temp
                def save_uploads(files):
                    paths = []
                    tmp_dir = tempfile.mkdtemp()
                    for f in files:
                        path = os.path.join(tmp_dir, f.name)
                        with open(path, "wb") as f_out:
                            f_out.write(f.getbuffer())
                        paths.append(path)
                    return paths, tmp_dir
                
                # 1. Ingest
                status.info("Ingesting XML files...")
                progress.progress(10)
                
                dtr_paths, dtr_tmp = save_uploads(dtr_files)
                nom_paths, nom_tmp = save_uploads(nom_files)
                txt_paths, txt_tmp = save_uploads(txt_files) if txt_files else ([], None)
                
                dtr_df = parse_xml_to_df(dtr_paths, "DTR")
                nom_df = parse_xml_to_df(nom_paths, "NOM")
                # txt_df = parse_xml_to_df(txt_paths, "TXT") # Not used in ZD14 yet?
                
                st.write(f"Loaded DTR: {len(dtr_df)} rows")
                st.write(f"Loaded NOM: {len(nom_df)} rows")
                
                # 2. Process
                status.info("Processing Data...")
                progress.progress(30)
                
                # DTR Processing
                dtr_df = cleanse_hs(dtr_df, 'hs')
                dtr_df = filter_active_country_groups(dtr_df, config)
                dtr_df = flag_hs(dtr_df, config, "DTR")
                
                # Filter Active only?
                # VBA Logic: Deletes '02-invalid' and '03-duplicate' usually before export or during export?
                # Actually mSubs DeleteEntries logic filters via ActiveCountryGroupList. 
                # ZD14 generation usually takes active VALID records.
                # Let's filter for '01-active'.
                dtr_active = dtr_df[dtr_df['hs_flag'] == '01-active'].copy()
                st.write(f"Active DTR Records: {len(dtr_active)}")
                
                # NOM Processing
                nom_df = cleanse_hs(nom_df, 'number') # Cleanse NOM number if needed?
                # Wait, NOM 'number' in XML sample matches DTR cleansed 'hs'? 
                # DTR '16055...' NOM '0102...'. 
                # If NOM has leading 00, cleanse it.
                nom_df = cleanse_hs(nom_df, 'number')
                
                nom_df = build_descriptions(nom_df)
                
                progress.progress(60)
                
                # 3. Export
                status.info("Generating ZD14...")
                
                zd14_df = generate_zd14(dtr_active, nom_df, config)
                
                st.write(f"Generated ZD14: {len(zd14_df)} rows")
                st.dataframe(zd14_df.head())
                
                progress.progress(90)
                
                # Save to specific output dir
                output_dir = "output_generated"
                export_csv_split(zd14_df, output_dir, f"{config.country} UPLOAD _ZD14")
                
                status.success("Processing Complete!")
                progress.progress(100)
                
                # Zip and download
                shutil.make_archive("output", 'zip', output_dir)
                
                with open("output.zip", "rb") as f:
                    st.download_button("Download Generated CSVs", f, "output.zip")
                    
                # Cleanup temps
                # shutil.rmtree(dtr_tmp) ...
                
            except Exception as e:
                st.error(f"Error occurred: {e}")
                logger.error(e, exc_info=True)
