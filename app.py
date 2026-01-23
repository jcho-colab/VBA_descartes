import streamlit as st
import pandas as pd
import os
import shutil
import tempfile
import logging
from pathlib import Path
from src.config import ConfigLoader
from src.ingest import parse_xml_to_df
from src.process import cleanse_hs, filter_active_country_groups, filter_by_chapter, flag_hs, build_descriptions
from src.export import generate_zd14, generate_capdr, generate_mx6digits, generate_zzde, generate_zzdf, export_csv_split
from src.validation import validate_rates, validate_config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

st.set_page_config(page_title="FTA Tariff Rates Processor", layout="wide", page_icon="📊")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📊 FTA Tariff Rates Processor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Python-based migration of Excel/VBA tariff processing system</div>', unsafe_allow_html=True)

# Initialize session state
if 'config' not in st.session_state:
    st.session_state['config'] = None
if 'processing_complete' not in st.session_state:
    st.session_state['processing_complete'] = False

# Sidebar Configuration
st.sidebar.header("⚙️ Configuration")

# Excel config path
default_excel_path = "/app/HS_IMP_v6.3.xlsm"
if not os.path.exists(default_excel_path):
    default_excel_path = "HS_IMP_v6.3.xlsm"

excel_path = st.sidebar.text_input(
    "Excel Config Path", 
    value=default_excel_path,
    help="Path to the HS_IMP Excel configuration file"
)

# Get available countries from Excel file for dropdown
available_countries = []
try:
    if os.path.exists(excel_path):
        import openpyxl
        wb = openpyxl.load_workbook(excel_path, data_only=True, read_only=True)
        config_sheet = wb["Config"]
        # Get all table names and extract country codes
        for table_name in config_sheet.tables.keys():
            if "RateType" in table_name:
                country = table_name.replace("RateType", "")
                if country and country not in available_countries:
                    available_countries.append(country)
        wb.close()
        available_countries = sorted(available_countries)
except:
    available_countries = ["NZ", "CA", "US", "MX", "BR", "EU"]  # Fallback

# Country selection dropdown
country_override = st.sidebar.selectbox(
    "Select Country",
    options=[""] + available_countries,
    index=0,
    help="Select a country to process. Leave blank to use the default country from Excel configuration."
)

# Load configuration
if st.sidebar.button("🔄 Load Configuration", type="primary"):
    if not os.path.exists(excel_path):
        st.sidebar.error(f"❌ Configuration file not found: {excel_path}")
    else:
        try:
            with st.spinner("Loading configuration..."):
                loader = ConfigLoader(excel_path)
                config = loader.load(country_override if country_override else None)
                st.session_state['config'] = config
                st.session_state['editable_year'] = config.year
                st.session_state['editable_min_chapter'] = config.min_chapter
                st.session_state['editable_max_csv'] = config.max_csv
                st.sidebar.success(f"✅ Config loaded: {config.country} ({config.year})")
                    
        except Exception as e:
            st.sidebar.error(f"❌ Failed to load config: {str(e)}")
            logger.error(f"Config load error: {e}", exc_info=True)

# Main content
if st.session_state['config'] is None:
    st.info("👈 Please load configuration from the sidebar to begin")
    st.stop()

config = st.session_state['config']

st.header(f"🌍 Processing for {config.country} - Year {config.year}")

# File Upload Section
st.subheader("📁 Upload XML Files")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**DTR Files** (Duty Rate)")
    dtr_files = st.file_uploader(
        "Upload DTR XML files", 
        type="xml", 
        accept_multiple_files=True,
        key="dtr_upload",
        help="Duty rate XML files (HSNZ_IMP_EN_DTR_I_*.xml)"
    )
    if dtr_files:
        st.success(f"✅ {len(dtr_files)} DTR file(s) uploaded")

with col2:
    st.markdown("**NOM Files** (Nomenclature)")
    nom_files = st.file_uploader(
        "Upload NOM XML files", 
        type="xml", 
        accept_multiple_files=True,
        key="nom_upload",
        help="Nomenclature XML files (HSNZ_IMP_EN_NOM_I_*.xml)"
    )
    if nom_files:
        st.success(f"✅ {len(nom_files)} NOM file(s) uploaded")

with col3:
    st.markdown("**TXT Files** (Text/Notes) - Optional")
    txt_files = st.file_uploader(
        "Upload TXT XML files", 
        type="xml", 
        accept_multiple_files=True,
        key="txt_upload",
        help="Text/notes XML files (HSNZ_IMP_EN_TXT_I_*.xml)"
    )
    if txt_files:
        st.success(f"✅ {len(txt_files)} TXT file(s) uploaded")

# Processing Options
st.subheader("⚙️ Processing Options")

col_opt1, col_opt2 = st.columns(2)

with col_opt1:
    skip_validation = st.checkbox(
        "Skip Validation Checks",
        value=False,
        help="Skip rate and config validation (not recommended)"
    )

with col_opt2:
    output_dir = st.text_input(
        "Output Directory",
        value="output_generated",
        help="Directory where CSV files will be saved"
    )

# Output types based on country
st.subheader("📊 Output Types to Generate")
output_types = {"ZD14": True}  # ZD14 always generated

if config.country == "CA":
    col_ca1, col_ca2 = st.columns(2)
    with col_ca1:
        output_types["CAPDR"] = st.checkbox("Generate CAPDR", value=True)
    with col_ca2:
        output_types["ZZDE"] = st.checkbox("Generate ZZDE", value=True)
elif config.country == "MX":
    output_types["MX6Digits"] = st.checkbox("Generate MX6Digits", value=True)
elif config.country == "US":
    output_types["ZZDF"] = st.checkbox("Generate ZZDF", value=True)

# Process Button
st.markdown("---")

if st.button("🚀 Run Processing Pipeline", type="primary", use_container_width=True):
    if not dtr_files or not nom_files:
        st.error("❌ Please upload at least DTR and NOM files")
    else:
        status_container = st.container()
        progress_bar = st.progress(0)
        
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
            
            # 1. INGEST
            status_container.info("📥 Step 1/6: Ingesting XML files...")
            progress_bar.progress(10)
            
            dtr_paths, dtr_tmp = save_uploads(dtr_files)
            nom_paths, nom_tmp = save_uploads(nom_files)
            txt_paths, txt_tmp = save_uploads(txt_files) if txt_files else ([], None)
            
            dtr_df = parse_xml_to_df(dtr_paths, "DTR")
            nom_df = parse_xml_to_df(nom_paths, "NOM")
            txt_df = parse_xml_to_df(txt_paths, "TXT") if txt_paths else pd.DataFrame()
            
            st.success(f"✅ Loaded: DTR={len(dtr_df)} rows, NOM={len(nom_df)} rows")
            
            # 2. VALIDATION
            if not skip_validation:
                status_container.info("✔️ Step 2/6: Validating data...")
                progress_bar.progress(20)
                
                # Rate validation
                rate_valid, invalid_hs = validate_rates(dtr_df, config)
                if not rate_valid:
                    with st.expander(f"⚠️ Warning: {len(invalid_hs)} HS codes missing rate text", expanded=False):
                        st.write(invalid_hs[:20])  # Show first 20
                        if len(invalid_hs) > 20:
                            st.write(f"... and {len(invalid_hs) - 20} more")
                    
                    if not st.checkbox("Continue despite missing rates?"):
                        st.stop()
                
                # Config validation (after creating concat_cg_drt)
                if 'country_group' in dtr_df.columns and 'duty_rate_type' in dtr_df.columns:
                    dtr_df['concat_cg_drt'] = dtr_df['country_group'].fillna('') + " " + dtr_df['duty_rate_type'].fillna('')
                
                config_valid, missing_items = validate_config(dtr_df, nom_df, config)
                if not config_valid:
                    with st.expander("⚠️ Warning: Unmapped configuration items", expanded=False):
                        if missing_items['country_groups']:
                            st.write("**Unmapped Country Groups:**", missing_items['country_groups'][:10])
                        if missing_items['uoms']:
                            st.write("**Unmapped UOMs:**", missing_items['uoms'][:10])
                    
                    if not st.checkbox("Continue despite config mismatches?"):
                        st.stop()
            else:
                progress_bar.progress(20)
            
            # 3. PROCESSING
            status_container.info("⚙️ Step 3/6: Processing DTR data...")
            progress_bar.progress(35)
            
            # DTR Processing
            dtr_df = cleanse_hs(dtr_df, 'hs')
            dtr_df = filter_by_chapter(dtr_df, config)
            dtr_df = filter_active_country_groups(dtr_df, config)
            dtr_df = flag_hs(dtr_df, config, "DTR")
            
            # Filter active only
            dtr_active = dtr_df[dtr_df['hs_flag'] == '01-active'].copy()
            st.success(f"✅ Active DTR records: {len(dtr_active)}/{len(dtr_df)}")
            
            # NOM Processing
            status_container.info("⚙️ Step 4/6: Processing NOM data...")
            progress_bar.progress(50)
            
            nom_df = cleanse_hs(nom_df, 'number')
            nom_df = flag_hs(nom_df, config, "NOM")
            nom_df = build_descriptions(nom_df)
            
            st.success(f"✅ Processed NOM: {len(nom_df)} records")
            
            # 4. GENERATE OUTPUTS
            status_container.info("📊 Step 5/6: Generating output datasets...")
            progress_bar.progress(65)
            
            outputs = {}
            
            if output_types.get("ZD14", True):
                outputs["ZD14"] = generate_zd14(dtr_active, nom_df, config)
                st.success(f"✅ Generated ZD14: {len(outputs['ZD14'])} rows")
            
            if output_types.get("CAPDR", False):
                outputs["CAPDR"] = generate_capdr(dtr_active, nom_df, config)
                if not outputs["CAPDR"].empty:
                    st.success(f"✅ Generated CAPDR: {len(outputs['CAPDR'])} rows")
            
            if output_types.get("MX6Digits", False):
                outputs["MX6Digits"] = generate_mx6digits(dtr_active, nom_df, config)
                if not outputs["MX6Digits"].empty:
                    st.success(f"✅ Generated MX6Digits: {len(outputs['MX6Digits'])} rows")
            
            if output_types.get("ZZDE", False):
                outputs["ZZDE"] = generate_zzde(dtr_active, nom_df, config)
                if not outputs["ZZDE"].empty:
                    st.success(f"✅ Generated ZZDE: {len(outputs['ZZDE'])} rows")
            
            if output_types.get("ZZDF", False):
                outputs["ZZDF"] = generate_zzdf(dtr_active, nom_df, config)
                if not outputs["ZZDF"].empty:
                    st.success(f"✅ Generated ZZDF: {len(outputs['ZZDF'])} rows")
            
            # 5. EXPORT
            status_container.info("💾 Step 6/6: Exporting CSV files...")
            progress_bar.progress(80)
            
            all_exported_files = []
            
            for output_type, df in outputs.items():
                if not df.empty:
                    prefix = f"{config.country} UPLOAD _{output_type}"
                    files = export_csv_split(df, output_dir, prefix, config.max_csv)
                    if files:
                        all_exported_files.extend(files)
            
            progress_bar.progress(90)
            
            # 6. CREATE ZIP
            if all_exported_files:
                status_container.info("📦 Creating download package...")
                
                zip_path = "output.zip"
                shutil.make_archive("output", 'zip', output_dir)
                
                progress_bar.progress(100)
                
                # Success message
                st.markdown('<div class="success-box">', unsafe_allow_html=True)
                st.markdown("### ✅ Processing Complete!")
                st.markdown(f"**Generated {len(all_exported_files)} CSV file(s)**")
                for f in all_exported_files:
                    st.markdown(f"- `{os.path.basename(f)}`")
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Download button
                with open(zip_path, "rb") as f:
                    st.download_button(
                        label="📥 Download All CSV Files (ZIP)",
                        data=f,
                        file_name=f"{config.country}_tariff_output_{config.year}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                
                # Preview first output
                if "ZD14" in outputs and not outputs["ZD14"].empty:
                    with st.expander("👀 Preview ZD14 Output (first 50 rows)"):
                        st.dataframe(outputs["ZD14"].head(50), use_container_width=True)
                
                st.session_state['processing_complete'] = True
            else:
                st.error("❌ No files were generated")
            
            # Cleanup temps
            try:
                if dtr_tmp and os.path.exists(dtr_tmp):
                    shutil.rmtree(dtr_tmp)
                if nom_tmp and os.path.exists(nom_tmp):
                    shutil.rmtree(nom_tmp)
                if txt_tmp and os.path.exists(txt_tmp):
                    shutil.rmtree(txt_tmp)
            except:
                pass
                
        except Exception as e:
            progress_bar.progress(0)
            st.markdown('<div class="error-box">', unsafe_allow_html=True)
            st.markdown(f"### ❌ Error Occurred")
            st.markdown(f"**Error:** {str(e)}")
            st.markdown('</div>', unsafe_allow_html=True)
            logger.error(f"Processing error: {e}", exc_info=True)
            
            with st.expander("🐛 View Error Details"):
                st.exception(e)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <small>FTA Tariff Rates Processor | Python Migration of Excel/VBA System<br>
    Supports: ZD14, CAPDR, MX6Digits, ZZDE, ZZDF output formats</small>
</div>
""", unsafe_allow_html=True)
