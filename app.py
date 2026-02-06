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
from src.export import generate_zd14, generate_capdr, generate_mx6digits, generate_zzde, generate_zzdf, export_csv_split, export_xlsx
from src.export_hs import generate_export_hs
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
    
    with st.sidebar.expander("✏️ Edit Settings", expanded=True):
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
tab_process, tab_export_hs, tab_info = st.tabs(["🚀 Import Tariffs", "📤 Export HS", "ℹ️ Reference Info"])

with tab_export_hs:
    st.markdown("##### 📁 Upload XML Files for Export HS")
    st.info("⚠️ Export HS processing uses **NOM** and **TXT** files only (no DTR required)")

    col1, col2 = st.columns(2)

    with col1:
        st.caption("**NOM** (Nomenclature) *required*")
        exp_nom_files_raw = st.file_uploader("NOM for Export", type="xml", accept_multiple_files=True, key="exp_nom_upload", label_visibility="collapsed")
        exp_nom_files = [f for f in exp_nom_files_raw if "NOM" in f.name.upper()] if exp_nom_files_raw else []

    with col2:
        st.caption("**TXT** (Text) *optional*")
        exp_txt_files_raw = st.file_uploader("TXT for Export", type="xml", accept_multiple_files=True, key="exp_txt_upload", label_visibility="collapsed")
        exp_txt_files = [f for f in exp_txt_files_raw if "TXT" in f.name.upper()] if exp_txt_files_raw else []

    file_status_exp = []
    if exp_nom_files:
        file_status_exp.append(f"✅ {len(exp_nom_files)} NOM")
    if exp_txt_files:
        file_status_exp.append(f"✅ {len(exp_txt_files)} TXT")
    if file_status_exp:
        st.caption(" | ".join(file_status_exp))

    st.markdown("##### ⚙️ Export Options")
    exp_opt_col1, exp_opt_col2 = st.columns(2)

    with exp_opt_col1:
        if 'exp_output_dir' not in st.session_state:
            st.session_state['exp_output_dir'] = "output_generated"
        st.caption("**Output Directory**")

        exp_dir_col1, exp_dir_col2 = st.columns([5, 1])
        with exp_dir_col1:
            exp_output_dir = st.text_input("Export Output Dir", value=st.session_state['exp_output_dir'], key="exp_output_dir_input", label_visibility="collapsed")
            st.session_state['exp_output_dir'] = exp_output_dir
        with exp_dir_col2:
            if st.button("📂", help="Browse for folder", key="exp_browse_btn"):
                try:
                    import tkinter as tk
                    from tkinter import filedialog
                    root = tk.Tk()
                    root.withdraw()
                    root.wm_attributes('-topmost', 1)
                    folder_selected = filedialog.askdirectory()
                    root.quit()
                    root.destroy()
                    if folder_selected:
                        st.session_state['exp_output_dir'] = folder_selected
                        st.rerun()
                except Exception as e:
                    st.toast(f"Folder browser error: {e}")

        exp_current_dir = os.getcwd()
        exp_full_output_path = os.path.join(exp_current_dir, exp_output_dir) if not os.path.isabs(exp_output_dir) else exp_output_dir
        st.caption(f"💾 `{exp_full_output_path}`")

    with exp_opt_col2:
        st.caption("**Export Format**")
        st.info("📊 XLSX format (single file)")

    exp_btn_col1, exp_btn_col2 = st.columns([1, 3])
    with exp_btn_col1:
        if st.button("🔄 Reset Export", use_container_width=True, key="exp_reset_btn"):
            for key in list(st.session_state.keys()):
                if key.startswith('exp_'):
                    del st.session_state[key]
            st.rerun()
    with exp_btn_col2:
        run_export_processing = st.button("🚀 Run Export HS Pipeline", type="primary", use_container_width=True, key="exp_run_btn")

    if run_export_processing:
        if not exp_nom_files:
            st.error("❌ Please upload NOM files")
        else:
            exp_progress_bar = st.progress(0)

            try:
                def save_uploads_exp(files):
                    paths = []
                    tmp_dir = tempfile.mkdtemp()
                    for f in files:
                        path = os.path.join(tmp_dir, f.name)
                        with open(path, "wb") as f_out:
                            f_out.write(f.getbuffer())
                        paths.append(path)
                    return paths, tmp_dir

                st.info("📥 Step 1/5: Ingesting XML files...")
                exp_progress_bar.progress(15)

                exp_nom_paths, exp_nom_tmp = save_uploads_exp(exp_nom_files)
                exp_txt_paths, exp_txt_tmp = save_uploads_exp(exp_txt_files) if exp_txt_files else ([], None)

                nom_df = parse_xml_to_df(exp_nom_paths, "NOM")
                txt_df = parse_xml_to_df(exp_txt_paths, "TXT") if exp_txt_paths else pd.DataFrame()

                st.success(f"✅ Loaded: NOM={len(nom_df)} rows" + (f", TXT={len(txt_df)} rows" if not txt_df.empty else ""))

                st.info("⚙️ Step 2/5: Processing NOM...")
                exp_progress_bar.progress(30)

                nom_df = cleanse_hs(nom_df, 'number')
                nom_df = filter_by_chapter(nom_df, config)
                nom_df = flag_hs(nom_df, config, "NOM", is_export=True)
                st.success(f"✅ Processed NOM: {len(nom_df)} records")

                st.info("⚙️ Step 3/5: Building descriptions...")
                exp_progress_bar.progress(50)

                nom_df = build_descriptions(nom_df)
                st.success(f"✅ Built hierarchical descriptions")

                st.info("📊 Step 4/5: Generating Export HS output...")
                exp_progress_bar.progress(70)

                export_hs_df = generate_export_hs(nom_df, txt_df, config)
                st.success(f"✅ Export HS: {len(export_hs_df)} rows")

                st.info("💾 Step 5/5: Exporting XLSX file...")
                exp_progress_bar.progress(85)

                exp_export_path = st.session_state.get('exp_output_dir', 'output_generated')
                if not os.path.isabs(exp_export_path):
                    exp_export_path = os.path.join(os.getcwd(), exp_export_path)
                os.makedirs(exp_export_path, exist_ok=True)

                exp_prefix = f"Exp{config.country}"
                exp_file_path = export_xlsx(export_hs_df, exp_export_path, exp_prefix, config.country)

                exp_progress_bar.progress(100)

                if exp_file_path:
                    st.markdown('<div class="success-box">', unsafe_allow_html=True)
                    st.markdown(f"### ✅ Complete! Generated Export HS file")
                    st.markdown('</div>', unsafe_allow_html=True)

                    with open(exp_file_path, "rb") as f:
                        st.download_button("📥 Download XLSX", data=f,
                                          file_name=os.path.basename(exp_file_path),
                                          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                          use_container_width=True)

                    with st.expander("👀 Preview Export HS (first 50 rows)"):
                        st.dataframe(export_hs_df.head(50), use_container_width=True)
                else:
                    st.error("❌ No file generated")

                for tmp in [exp_nom_tmp, exp_txt_tmp]:
                    if tmp and os.path.exists(tmp):
                        shutil.rmtree(tmp, ignore_errors=True)

            except Exception as e:
                exp_progress_bar.progress(0)
                st.markdown('<div class="error-box">', unsafe_allow_html=True)
                st.markdown(f"### ❌ Error: {str(e)}")
                st.markdown('</div>', unsafe_allow_html=True)
                logger.error(f"Export processing error: {e}", exc_info=True)
                with st.expander("🐛 Details"):
                    st.exception(e)

with tab_info:
    col1, col2 = st.columns(2)
    # ---- LEFT TABLE ----
    with col1:
        st.markdown("#### Duty Rate Type Definitions")

        drt_df = pd.DataFrame(
            [{"Code": k, "Definition": v} for k, v in DUTY_RATE_TYPE_DEFINITIONS.items()]
        )

        # Fixed widths (in pixels)
        column_widths = {
            "Code": 50,
            "Definition": 200,
        }


        styles = []
        for col in drt_df.columns:
            width = column_widths[col]
            idx = list(drt_df.columns).index(col)

            styles += [
                {'selector': f'th.col_heading.level0.col{idx}', 'props': [('min-width', f'{width}px')]},
                {'selector': f'td.col{idx}', 'props': [('min-width', f'{width}px')]}
            ]

        drt_df_styled = drt_df.style.set_table_styles(styles)

        st.dataframe(drt_df_styled, use_container_width=True, hide_index=True, height=300)

    # ---- RIGHT TABLE ----
    with col2:
        st.markdown("#### Current Configuration - Rate Types")
        if not config.rate_type_defs.empty:
            st.dataframe(
                config.rate_type_defs,
                use_container_width=True,
                hide_index=True,
                height=300
            )
        else:
            st.info("No rate types configured")

    # st.markdown("#### Duty Rate Type Definitions")
    # drt_df = pd.DataFrame([{"Code": k, "Definition": v} for k, v in DUTY_RATE_TYPE_DEFINITIONS.items()])
    # st.dataframe(drt_df, use_container_width=True, hide_index=True, height=300)
    
    # st.markdown("#### Current Configuration - Rate Types")
    # if not config.rate_type_defs.empty:
    #     st.dataframe(config.rate_type_defs, use_container_width=True, hide_index=True, height=250)
    # else:
    #     st.info("No rate types configured")

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
        # if 'output_dir' not in st.session_state:
        #     st.session_state['output_dir'] = "output_generated"
        st.session_state['output_dir'] = r"S:\Shared\Finances\Douane\Global Content (HS Tariff)\Tariff_Update_Descartes\_v_ImpHS_Template"
        st.caption("**Output Directory**")
        
        dir_col1, dir_col2 = st.columns([5, 1])
        with dir_col1:
            output_dir = st.text_input("Output Dir", value=st.session_state['output_dir'], key="output_dir_input", label_visibility="collapsed")
            st.session_state['output_dir'] = output_dir
        with dir_col2:
            # st.markdown("ℹ️", help="Enter folder path directly in the text field")
            if st.button("📂", help="Browse for folder", key="browse_btn"):
                try:
                    import tkinter as tk
                    from tkinter import filedialog
                    root = tk.Tk()
                    root.withdraw()
                    root.wm_attributes('-topmost', 1)
                    folder_selected = filedialog.askdirectory(initialdir=r"S:\Shared\Finances\Douane\Global Content (HS Tariff)\Tariff_Update_Descartes\_v_ImpHS_Template")
                    root.quit()
                    root.destroy()
                    if folder_selected:
                        st.session_state['output_dir'] = folder_selected
                        st.rerun()
                except Exception as e:
                    st.toast(f"Folder browser error: {e}")
        
        current_dir = os.getcwd()
        full_output_path = os.path.join(current_dir, output_dir) if not os.path.isabs(output_dir) else output_dir
        st.caption(f"💾 `{full_output_path}`")
    
    with opt_col3:
        st.caption("**Output Types**")
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
                # Use the full output path from session state
                export_path = st.session_state.get('output_dir', 'output_generated')
                if not os.path.isabs(export_path):
                    export_path = os.path.join(os.getcwd(), export_path)
                os.makedirs(export_path, exist_ok=True)
                
                for output_type, df in outputs.items():
                    if not df.empty:
                        prefix = f"{config.country} UPLOAD _{output_type}"
                        files = export_csv_split(df, export_path, prefix, config.max_csv)
                        if files:
                            all_exported_files.extend(files)
                
                progress_bar.progress(90)
                
                if all_exported_files:
                    zip_path = "output.zip"
                    shutil.make_archive("output", 'zip', export_path)
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
st.markdown("<div style='text-align: center; color: #888; font-size: 0.8rem;'>FTA Tariff Processor | Import Tariffs (ZD14, CAPDR, MX6Digits, ZZDE, ZZDF) + Export HS</div>", unsafe_allow_html=True)
