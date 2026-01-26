import streamlit as st
import pandas as pd
import os
import shutil
import tempfile
import logging
from pathlib import Path
from src.config import ConfigLoader, DUTY_RATE_TYPE_DEFINITIONS
from src.ingest import parse_xml_to_df, parse_country_group_definitions
from src.process import cleanse_hs, filter_active_country_groups, filter_by_chapter, flag_hs, build_descriptions
from src.export import generate_zd14, generate_capdr, generate_mx6digits, generate_zzde, generate_zzdf, export_csv_split
from src.validation import validate_rates, validate_config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

st.set_page_config(page_title="FTA Tariff Rates Processor", layout="wide", page_icon="📊")

# Compact CSS - minimize spacing and scrolling
st.markdown("""
<style>
    .main-header { font-size: 1.8rem; font-weight: bold; color: #1f77b4; margin-bottom: 0.3rem; }
    .sub-header { font-size: 0.95rem; color: #666; margin-bottom: 0.8rem; }
    .success-box { padding: 0.6rem; background-color: #d4edda; border-left: 4px solid #28a745; margin: 0.5rem 0; }
    .warning-box { padding: 0.6rem; background-color: #fff3cd; border-left: 4px solid #ffc107; margin: 0.5rem 0; }
    .error-box { padding: 0.6rem; background-color: #f8d7da; border-left: 4px solid #dc3545; margin: 0.5rem 0; }
    .main-cg-box { padding: 0.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   border-radius: 6px; color: white; margin: 0.3rem 0; }
    .main-cg-label { font-size: 0.7rem; opacity: 0.9; margin-bottom: 2px; }
    .main-cg-value { font-size: 1.1rem; font-weight: bold; }
    .main-cg-desc { font-size: 0.75rem; opacity: 0.85; margin-top: 2px; }
    .config-stat { display: inline-block; padding: 2px 8px; background: #f0f2f6; border-radius: 4px; 
                   margin: 2px 4px 2px 0; font-size: 0.75rem; }
    /* Reduce all spacing */
    section[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem; }
    .block-container { padding-top: 0.5rem; padding-bottom: 0; }
    div[data-testid="stExpander"] { margin-bottom: 0.3rem; }
    .stButton > button { padding: 0.3rem 1rem; }
    h1, h2, h3 { margin-top: 0.5rem; margin-bottom: 0.3rem; }
    .element-container { margin-bottom: 0.3rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📊 FTA Tariff Rates Processor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Python-based migration of Excel/VBA tariff processing system</div>', unsafe_allow_html=True)

# Initialize session state
if 'config' not in st.session_state:
    st.session_state['config'] = None
if 'processing_complete' not in st.session_state:
    st.session_state['processing_complete'] = False

# Sidebar Configuration - Compact Layout
st.sidebar.markdown("### ⚙️ Configuration")

CONFIG_DIR = "Configuration_files"
loader = ConfigLoader(CONFIG_DIR)
available_countries = loader.get_available_countries()

# Country selection and load button on same row concept - keep compact
country_override = st.sidebar.selectbox(
    "Country", options=[""] + available_countries, index=0,
    help="Select country to process", label_visibility="collapsed"
)

if st.sidebar.button("🔄 Load Configuration", type="primary", use_container_width=True):
    if not os.path.exists(CONFIG_DIR):
        st.sidebar.error(f"❌ Config dir not found")
    else:
        try:
            config = loader.load(country_override if country_override else None)
            st.session_state['config'] = config
            st.session_state['editable_year'] = config.year
            st.session_state['editable_min_chapter'] = config.min_chapter
            st.session_state['editable_max_csv'] = config.max_csv
        except Exception as e:
            st.sidebar.error(f"❌ {str(e)[:50]}")
            logger.error(f"Config load error: {e}", exc_info=True)

# Display config details when loaded - COMPACT
if st.session_state['config'] is not None:
    cfg = st.session_state['config']
    
    # Main Country Group - Prominent Display
    st.sidebar.markdown(f"""
    <div class="main-cg-box">
        <div class="main-cg-label">MAIN COUNTRY GROUP</div>
        <div class="main-cg-value">{cfg.main_country_group}</div>
        <div class="main-cg-desc">{cfg.main_country_group_description}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Compact config summary
    st.sidebar.markdown(f"""
    <div style="margin: 0.3rem 0;">
        <span class="config-stat">🌍 {cfg.country}</span>
        <span class="config-stat">📅 {cfg.year}</span>
        <span class="config-stat">📊 Ch≥{cfg.min_chapter}</span>
    </div>
    <div style="margin: 0.3rem 0;">
        <span class="config-stat">✅ {len(cfg.active_country_group_list)} Active CG</span>
        <span class="config-stat">📏 {len(cfg.uom_dict)} UOMs</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Editable settings in collapsed expander
    with st.sidebar.expander("✏️ Edit Settings", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            new_year = st.text_input("Year", value=st.session_state.get('editable_year', '2026'), key="year_input")
            if new_year:
                try:
                    if 2000 <= int(new_year) <= 2100:
                        st.session_state['editable_year'] = new_year
                        st.session_state['config'].year = new_year
                except ValueError:
                    pass
        with col2:
            new_min = st.number_input("Min Ch", 1, 99, st.session_state.get('editable_min_chapter', 25), key="min_ch")
            st.session_state['editable_min_chapter'] = new_min
            st.session_state['config'].min_chapter = int(new_min)
            st.session_state['config'].chapter_list = [str(i).zfill(2) for i in range(int(new_min), 100)]
        
        new_max = st.number_input("Max CSV Rows", 1000, 10000000, 
                                   st.session_state.get('editable_max_csv', 30000), 10000, key="max_csv")
        st.session_state['editable_max_csv'] = new_max
        st.session_state['config'].max_csv = new_max

# Main content
if st.session_state['config'] is None:
    st.info("👈 Select a country and click **Load Configuration** to begin")
    
    # Show Info tab even without config
    st.markdown("---")
    st.subheader("ℹ️ Reference Information")
    st.markdown("**Duty Rate Type Definitions**")
    drt_df = pd.DataFrame([
        {"Code": k, "Definition": v} for k, v in DUTY_RATE_TYPE_DEFINITIONS.items()
    ])
    st.dataframe(drt_df, use_container_width=True, hide_index=True, height=300)
    st.stop()

config = st.session_state['config']

# File Upload Section
st.subheader("📁 Upload XML Files")

# Helper function to filter files by pattern
def filter_files_by_pattern(files, pattern):
    """Filter uploaded files by filename pattern."""
    if not files:
        return []
    filtered = [f for f in files if pattern.upper() in f.name.upper()]
    return filtered

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**DTR Files** (Duty Rate)")
    st.caption("📌 Expected pattern: *DTR*.xml")
    dtr_files_raw = st.file_uploader(
        "Upload DTR XML files", 
        type="xml", 
        accept_multiple_files=True,
        key="dtr_upload",
        help="Duty rate XML files matching pattern: *DTR*.xml (e.g., HSNZ_IMP_EN_DTR_I_00044001001.xml)"
    )
    
    # Filter DTR files
    dtr_files = filter_files_by_pattern(dtr_files_raw, "DTR")
    
    if dtr_files_raw:
        if dtr_files:
            st.success(f"✅ {len(dtr_files)} DTR file(s) uploaded")
        else:
            st.error(f"❌ No DTR files found. Please upload files containing 'DTR' in the filename.")
        
        # Show non-DTR files that were uploaded
        non_dtr = [f.name for f in dtr_files_raw if f not in dtr_files]
        if non_dtr:
            st.warning(f"⚠️ Ignored {len(non_dtr)} non-DTR file(s)")
            with st.expander("View ignored files"):
                for fname in non_dtr:
                    st.caption(f"• {fname}")

with col2:
    st.markdown("**NOM Files** (Nomenclature)")
    st.caption("📌 Expected pattern: *NOM*.xml")
    nom_files_raw = st.file_uploader(
        "Upload NOM XML files", 
        type="xml", 
        accept_multiple_files=True,
        key="nom_upload",
        help="Nomenclature XML files matching pattern: *NOM*.xml (e.g., HSNZ_IMP_EN_NOM_I_00044001003.xml)"
    )
    
    # Filter NOM files
    nom_files = filter_files_by_pattern(nom_files_raw, "NOM")
    
    if nom_files_raw:
        if nom_files:
            st.success(f"✅ {len(nom_files)} NOM file(s) uploaded")
        else:
            st.error(f"❌ No NOM files found. Please upload files containing 'NOM' in the filename.")
        
        # Show non-NOM files
        non_nom = [f.name for f in nom_files_raw if f not in nom_files]
        if non_nom:
            st.warning(f"⚠️ Ignored {len(non_nom)} non-NOM file(s)")
            with st.expander("View ignored files"):
                for fname in non_nom:
                    st.caption(f"• {fname}")

with col3:
    st.markdown("**TXT Files** (Text/Notes) - Optional")
    st.caption("📌 Expected pattern: *TXT*.xml")
    txt_files_raw = st.file_uploader(
        "Upload TXT XML files", 
        type="xml", 
        accept_multiple_files=True,
        key="txt_upload",
        help="Text/notes XML files matching pattern: *TXT*.xml (e.g., HSNZ_IMP_EN_TXT_I_00044001001.xml)"
    )
    
    # Filter TXT files
    txt_files = filter_files_by_pattern(txt_files_raw, "TXT")
    
    if txt_files_raw:
        if txt_files:
            st.success(f"✅ {len(txt_files)} TXT file(s) uploaded")
        else:
            st.error(f"❌ No TXT files found. Please upload files containing 'TXT' in the filename.")
        
        # Show non-TXT files
        non_txt = [f.name for f in txt_files_raw if f not in txt_files]
        if non_txt:
            st.warning(f"⚠️ Ignored {len(non_txt)} non-TXT file(s)")
            with st.expander("View ignored files"):
                for fname in non_txt:
                    st.caption(f"• {fname}")

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
    # Output directory with better UI
    st.markdown("**Output Directory**")
    
    # Show current working directory as reference
    current_dir = os.getcwd()
    st.caption(f"📁 Current directory: {current_dir}")
    
    # Initialize output_dir in session state if not present
    if 'output_dir' not in st.session_state:
        st.session_state['output_dir'] = "output_generated"
    
    # Create two columns for path input and browse button
    path_col, browse_col = st.columns([5, 1])
    
    with path_col:
        output_dir = st.text_input(
            "Save location",
            value=st.session_state['output_dir'],
            help="Directory where CSV files will be saved. Use relative or absolute path.",
            label_visibility="collapsed",
            key="output_dir_input"
        )
        st.session_state['output_dir'] = output_dir
    
    with browse_col:
        if st.button("📂", help="Browse for folder - opens folder selector dialog", key="browse_btn"):
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.wm_attributes('-topmost', 1)
                folder_selected = filedialog.askdirectory(initialdir=current_dir)
                root.destroy()
                if folder_selected:
                    st.session_state['output_dir'] = folder_selected
                    st.rerun()
            except Exception:
                st.warning("Folder browser not available. Please paste the path manually.")
    
    # Ensure output_dir is a string
    output_dir = str(st.session_state.get('output_dir', 'output_generated'))
    
    # Show full path that will be used
    if not os.path.isabs(output_dir):
        full_output_path = os.path.join(current_dir, output_dir)
    else:
        full_output_path = output_dir
    
    st.caption(f"💾 Files will be saved to: `{full_output_path}`")
    
    # Button to create directory if it doesn't exist
    if not os.path.exists(full_output_path):
        if st.button("📁 Create Directory", key="create_output_dir"):
            try:
                os.makedirs(full_output_path, exist_ok=True)
                st.success(f"✅ Directory created: {full_output_path}")
            except Exception as e:
                st.error(f"❌ Failed to create directory: {e}")
    else:
        st.success("✅ Directory exists")

# Output types based on country (ZD14 always generated)
output_types = {"ZD14": True}

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

# Reset and Process Buttons
st.markdown("---")
col_reset, col_process = st.columns([1, 4])

with col_reset:
    if st.button("🔄 Reset", type="secondary", use_container_width=True, help="Reset all settings and start over"):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

with col_process:
    run_processing = st.button("🚀 Run Processing Pipeline", type="primary", use_container_width=True)

if run_processing:
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
            
            # Parse country group definitions for descriptions
            cg_descriptions = parse_country_group_definitions(dtr_paths)
            
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
                
                # Config validation - now blocks on new country groups
                config_valid, missing_items = validate_config(dtr_df, nom_df, config, cg_descriptions)
                
                # BLOCKING: New country groups detected
                if missing_items['country_groups']:
                    st.error("🚫 **New Country Groups Detected - Action Required**")
                    st.markdown("""
                    The following country groups were found in your XML files but are **not configured** 
                    in the configuration file. Processing cannot continue until these are added.
                    """)
                    
                    # Show the new country groups with ready-to-copy JSON in a single block
                    st.markdown("**Add the following entries to the config file:**")
                    
                    config_file = f"Configuration_files/{config.country.lower()}_config.json"
                    
                    # Build all JSON entries as a single block
                    json_entries = []
                    for cg_info in missing_items['country_groups']:
                        cg_id = cg_info['cg']
                        duty_type = cg_info['duty_rate_type']
                        description = cg_info['description']
                        json_entries.append(f'{{"Descartes CG": "{cg_id} {duty_type}", "Comment": "keep", "Description": "{description}"}}')
                    
                    # Display all entries in one code block
                    st.code(",\n".join(json_entries), language="json")
                    
                    st.markdown(f"""
                    ### How to fix:
                    1. Open `{config_file}`
                    2. Copy the JSON entries above into the `rate_types` array
                    3. Set `Comment` to `"keep"` to include it in processing, or `"remove"` to exclude it
                    4. Save the file and click **Load Configuration** again
                    5. Re-upload your XML files and run processing
                    """)
                    
                    st.warning("⚠️ Processing stopped. Please update the configuration file and try again.")
                    progress_bar.progress(0)
                    st.stop()
                
                # Show informational message about unmapped UOMs (not blocking)
                if missing_items['uoms']:
                    with st.expander("ℹ️ Info: New UOMs found (will use original values)", expanded=False):
                        st.caption("These UOMs are not in the configuration and will use their original XML values.")
                        for uom in missing_items['uoms'][:10]:
                            st.caption(f"  • {uom}")
                        if len(missing_items['uoms']) > 10:
                            st.caption(f"  ... and {len(missing_items['uoms']) - 10} more")
                        
                        st.info(f"💡 To add SAP mappings for these UOMs, edit `Configuration_files/{config.country.lower()}_config.json`")
                
                st.info("✅ Validation complete - ready to process")
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
