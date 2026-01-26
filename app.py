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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

st.set_page_config(page_title="FTA Tariff Rates Processor", layout="wide", page_icon="📊")

# Compact CSS
st.markdown("""
<style>
    .main-header { font-size: 1.8rem; font-weight: bold; color: #1f77b4; margin-bottom: 0.3rem; }
    .sub-header { font-size: 0.95rem; color: #666; margin-bottom: 0.5rem; }
    .success-box { padding: 0.5rem; background-color: #d4edda; border-left: 4px solid #28a745; margin: 0.4rem 0; }
    .error-box { padding: 0.5rem; background-color: #f8d7da; border-left: 4px solid #dc3545; margin: 0.4rem 0; }
    .main-cg-box { padding: 0.4rem 0.6rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   border-radius: 6px; color: white; margin: 0.3rem 0; }
    .main-cg-label { font-size: 0.65rem; opacity: 0.9; }
    .main-cg-value { font-size: 1rem; font-weight: bold; }
    .main-cg-desc { font-size: 0.7rem; opacity: 0.85; }
    .config-stat { display: inline-block; padding: 2px 6px; background: #f0f2f6; border-radius: 4px; 
                   margin: 2px 3px 2px 0; font-size: 0.7rem; }
    section[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem; }
    .block-container { padding-top: 0.5rem; }
    div[data-testid="stExpander"] { margin-bottom: 0.2rem; }
    h1, h2, h3 { margin-top: 0.4rem; margin-bottom: 0.2rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📊 FTA Tariff Rates Processor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Python-based migration of Excel/VBA tariff processing system</div>', unsafe_allow_html=True)

# Session state init
if 'config' not in st.session_state:
    st.session_state['config'] = None
if 'processing_complete' not in st.session_state:
    st.session_state['processing_complete'] = False

# Sidebar - Compact
st.sidebar.markdown("### ⚙️ Configuration")
CONFIG_DIR = "Configuration_files"
loader = ConfigLoader(CONFIG_DIR)
available_countries = loader.get_available_countries()

country_override = st.sidebar.selectbox("Country", options=[""] + available_countries, index=0, label_visibility="collapsed")

if st.sidebar.button("🔄 Load Configuration", type="primary", use_container_width=True):
    if os.path.exists(CONFIG_DIR):
        try:
            config = loader.load(country_override if country_override else None)
            st.session_state['config'] = config
            st.session_state['editable_year'] = config.year
            st.session_state['editable_min_chapter'] = config.min_chapter
            st.session_state['editable_max_csv'] = config.max_csv
        except Exception as e:
            st.sidebar.error(f"❌ {str(e)[:50]}")
            logger.error(f"Config load error: {e}", exc_info=True)
    else:
        st.sidebar.error("❌ Config dir not found")

# Sidebar config display
if st.session_state['config'] is not None:
    cfg = st.session_state['config']
    
    st.sidebar.markdown(f"""
    <div class="main-cg-box">
        <div class="main-cg-label">MAIN COUNTRY GROUP</div>
        <div class="main-cg-value">{cfg.main_country_group}</div>
        <div class="main-cg-desc">{cfg.main_country_group_description}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown(f"""
    <div style="margin: 0.2rem 0;">
        <span class="config-stat">🌍 {cfg.country}</span>
        <span class="config-stat">📅 {cfg.year}</span>
        <span class="config-stat">📊 Ch≥{cfg.min_chapter}</span>
    </div>
    <div style="margin: 0.2rem 0;">
        <span class="config-stat">✅ {len(cfg.active_country_group_list)} Active CG</span>
        <span class="config-stat">📏 {len(cfg.uom_dict)} UOMs</span>
    </div>
    """, unsafe_allow_html=True)
    
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
        
        new_max = st.number_input("Max CSV Rows", 1000, 10000000, st.session_state.get('editable_max_csv', 30000), 10000, key="max_csv")
        st.session_state['editable_max_csv'] = new_max
        st.session_state['config'].max_csv = new_max

# Main content
if st.session_state['config'] is None:
    st.info("👈 Select a country and click **Load Configuration** to begin")
    st.markdown("---")
    st.subheader("ℹ️ Reference Information")
    drt_df = pd.DataFrame([{"Code": k, "Definition": v} for k, v in DUTY_RATE_TYPE_DEFINITIONS.items()])
    st.dataframe(drt_df, use_container_width=True, hide_index=True, height=350)
    st.stop()

config = st.session_state['config']

# Tabs
tab_process, tab_info = st.tabs(["🚀 Processing", "ℹ️ Reference Info"])

with tab_info:
    st.markdown("#### Duty Rate Type Definitions")
    drt_df = pd.DataFrame([{"Code": k, "Definition": v} for k, v in DUTY_RATE_TYPE_DEFINITIONS.items()])
    st.dataframe(drt_df, use_container_width=True, hide_index=True, height=300)
    
    st.markdown("#### Current Configuration - Rate Types")
    if not config.rate_type_defs.empty:
        st.dataframe(config.rate_type_defs, use_container_width=True, hide_index=True, height=250)
    else:
        st.info("No rate types configured")

with tab_process:
    def filter_files_by_pattern(files, pattern):
        if not files:
            return []
        return [f for f in files if pattern.upper() in f.name.upper()]

    st.markdown("##### 📁 Upload XML Files")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.caption("**DTR** (Duty Rate) *required*")
        dtr_files_raw = st.file_uploader("DTR", type="xml", accept_multiple_files=True, key="dtr_upload", label_visibility="collapsed")
        dtr_files = filter_files_by_pattern(dtr_files_raw, "DTR")

    with col2:
        st.caption("**NOM** (Nomenclature) *required*")
        nom_files_raw = st.file_uploader("NOM", type="xml", accept_multiple_files=True, key="nom_upload", label_visibility="collapsed")
        nom_files = filter_files_by_pattern(nom_files_raw, "NOM")

    with col3:
        st.caption("**TXT** (Text) *optional*")
        txt_files_raw = st.file_uploader("TXT", type="xml", accept_multiple_files=True, key="txt_upload", label_visibility="collapsed")
        txt_files = filter_files_by_pattern(txt_files_raw, "TXT")

    # Show file counts inline
    file_status = []
    if dtr_files:
        file_status.append(f"✅ {len(dtr_files)} DTR")
    if nom_files:
        file_status.append(f"✅ {len(nom_files)} NOM")
    if txt_files:
        file_status.append(f"✅ {len(txt_files)} TXT")
    if file_status:
        st.caption(" | ".join(file_status))

    st.markdown("##### ⚙️ Options")
    opt_col1, opt_col2, opt_col3 = st.columns([1, 2, 2])
    
    with opt_col1:
        skip_validation = st.checkbox("Skip Validation", value=False)
    
    with opt_col2:
        if 'output_dir' not in st.session_state:
            st.session_state['output_dir'] = "output_generated"
        st.caption("**Output Directory**")
        output_dir = st.text_input("Output Dir", value=st.session_state['output_dir'], key="output_dir_input", label_visibility="collapsed")
        st.session_state['output_dir'] = output_dir
        current_dir = os.getcwd()
        full_output_path = os.path.join(current_dir, output_dir) if not os.path.isabs(output_dir) else output_dir
    
    with opt_col3:
        output_types = {"ZD14": True}
        if config.country == "CA":
            c1, c2 = st.columns(2)
            with c1:
                output_types["CAPDR"] = st.checkbox("CAPDR", value=True)
            with c2:
                output_types["ZZDE"] = st.checkbox("ZZDE", value=True)
        elif config.country == "MX":
            output_types["MX6Digits"] = st.checkbox("MX6Digits", value=True)
        elif config.country == "US":
            output_types["ZZDF"] = st.checkbox("ZZDF", value=True)

    btn_col1, btn_col2 = st.columns([1, 3])
    with btn_col1:
        if st.button("🔄 Reset", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    with btn_col2:
        run_processing = st.button("🚀 Run Processing Pipeline", type="primary", use_container_width=True)

    if run_processing:
        if not dtr_files or not nom_files:
            st.error("❌ Please upload DTR and NOM files")
        else:
            progress_bar = st.progress(0)
            
            try:
                def save_uploads(files):
                    paths = []
                    tmp_dir = tempfile.mkdtemp()
                    for f in files:
                        path = os.path.join(tmp_dir, f.name)
                        with open(path, "wb") as f_out:
                            f_out.write(f.getbuffer())
                        paths.append(path)
                    return paths, tmp_dir
                
                st.info("📥 Step 1/6: Ingesting XML files...")
                progress_bar.progress(10)
                
                dtr_paths, dtr_tmp = save_uploads(dtr_files)
                nom_paths, nom_tmp = save_uploads(nom_files)
                txt_paths, txt_tmp = save_uploads(txt_files) if txt_files else ([], None)
                
                dtr_df = parse_xml_to_df(dtr_paths, "DTR")
                nom_df = parse_xml_to_df(nom_paths, "NOM")
                txt_df = parse_xml_to_df(txt_paths, "TXT") if txt_paths else pd.DataFrame()
                cg_descriptions = parse_country_group_definitions(dtr_paths)
                
                st.success(f"✅ Loaded: DTR={len(dtr_df)}, NOM={len(nom_df)} rows")
                
                if not skip_validation:
                    st.info("✔️ Step 2/6: Validating...")
                    progress_bar.progress(20)
                    
                    rate_valid, invalid_hs = validate_rates(dtr_df, config)
                    if not rate_valid:
                        with st.expander(f"⚠️ {len(invalid_hs)} HS codes missing rate text"):
                            st.write(invalid_hs[:20])
                    
                    config_valid, missing_items = validate_config(dtr_df, nom_df, config, cg_descriptions)
                    
                    if missing_items['country_groups']:
                        st.error("🚫 New Country Groups Detected - Update config first")
                        config_file = f"Configuration_files/{config.country.lower()}_config.json"
                        json_entries = []
                        for cg_info in missing_items['country_groups']:
                            json_entries.append(f'{{"Descartes CG": "{cg_info["cg"]} {cg_info["duty_rate_type"]}", "Comment": "keep", "Description": "{cg_info["description"]}"}}')
                        st.code(",\n".join(json_entries), language="json")
                        st.warning(f"Add above to {config_file} and reload")
                        st.stop()
                else:
                    progress_bar.progress(20)
                
                st.info("⚙️ Step 3/6: Processing DTR...")
                progress_bar.progress(35)
                
                dtr_df = cleanse_hs(dtr_df, 'hs')
                dtr_df = filter_by_chapter(dtr_df, config)
                dtr_df = filter_active_country_groups(dtr_df, config)
                dtr_df = flag_hs(dtr_df, config, "DTR")
                dtr_active = dtr_df[dtr_df['hs_flag'] == '01-active'].copy()
                st.success(f"✅ Active DTR: {len(dtr_active)}/{len(dtr_df)}")
                
                st.info("⚙️ Step 4/6: Processing NOM...")
                progress_bar.progress(50)
                
                nom_df = cleanse_hs(nom_df, 'number')
                nom_df = flag_hs(nom_df, config, "NOM")
                nom_df = build_descriptions(nom_df)
                st.success(f"✅ NOM: {len(nom_df)} records")
                
                st.info("📊 Step 5/6: Generating outputs...")
                progress_bar.progress(65)
                
                outputs = {}
                if output_types.get("ZD14", True):
                    outputs["ZD14"] = generate_zd14(dtr_active, nom_df, config)
                    st.success(f"✅ ZD14: {len(outputs['ZD14'])} rows")
                
                if output_types.get("CAPDR"):
                    outputs["CAPDR"] = generate_capdr(dtr_active, nom_df, config)
                if output_types.get("MX6Digits"):
                    outputs["MX6Digits"] = generate_mx6digits(dtr_active, nom_df, config)
                if output_types.get("ZZDE"):
                    outputs["ZZDE"] = generate_zzde(dtr_active, nom_df, config)
                if output_types.get("ZZDF"):
                    outputs["ZZDF"] = generate_zzdf(dtr_active, nom_df, config)
                
                st.info("💾 Step 6/6: Exporting CSV files...")
                progress_bar.progress(80)
                
                all_exported_files = []
                for output_type, df in outputs.items():
                    if not df.empty:
                        prefix = f"{config.country} UPLOAD _{output_type}"
                        files = export_csv_split(df, output_dir, prefix, config.max_csv)
                        if files:
                            all_exported_files.extend(files)
                
                progress_bar.progress(90)
                
                if all_exported_files:
                    zip_path = "output.zip"
                    shutil.make_archive("output", 'zip', output_dir)
                    progress_bar.progress(100)
                    
                    st.markdown('<div class="success-box">', unsafe_allow_html=True)
                    st.markdown(f"### ✅ Complete! Generated {len(all_exported_files)} file(s)")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    with open(zip_path, "rb") as f:
                        st.download_button("📥 Download ZIP", data=f, 
                                          file_name=f"{config.country}_tariff_{config.year}.zip",
                                          mime="application/zip", use_container_width=True)
                    
                    if "ZD14" in outputs and not outputs["ZD14"].empty:
                        with st.expander("👀 Preview ZD14 (first 50 rows)"):
                            st.dataframe(outputs["ZD14"].head(50), use_container_width=True)
                else:
                    st.error("❌ No files generated")
                
                # Cleanup
                for tmp in [dtr_tmp, nom_tmp, txt_tmp]:
                    if tmp and os.path.exists(tmp):
                        shutil.rmtree(tmp, ignore_errors=True)
                        
            except Exception as e:
                progress_bar.progress(0)
                st.markdown('<div class="error-box">', unsafe_allow_html=True)
                st.markdown(f"### ❌ Error: {str(e)}")
                st.markdown('</div>', unsafe_allow_html=True)
                logger.error(f"Processing error: {e}", exc_info=True)
                with st.expander("🐛 Details"):
                    st.exception(e)

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: #888; font-size: 0.8rem;'>FTA Tariff Processor | ZD14, CAPDR, MX6Digits, ZZDE, ZZDF</div>", unsafe_allow_html=True)
