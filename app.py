import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
from io import BytesIO
import numpy as np
from datetime import datetime

# Page setup
st.set_page_config(
    page_title="DataViz Studio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Light custom styling
st.markdown("""
<style>
    .stButton > button { font-weight: 600; }
    .stDownloadButton > button { background-color: #0e7c7b; color: white; border: none; }
    .main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
</style>
""", unsafe_allow_html=True)

st.title("📊 DataViz Studio")
st.caption("Upload • Edit • Customize • Visualize • Download  •  Full faceting • No coding needed")

# Session state init
if 'df' not in st.session_state:
    st.session_state.df = None
if 'original_df' not in st.session_state:
    st.session_state.original_df = None
if 'last_fig' not in st.session_state:
    st.session_state.last_fig = None
if 'plot_config' not in st.session_state:
    st.session_state.plot_config = {}
if 'plot_type' not in st.session_state:
    st.session_state.plot_type = None
if 'dashboard_plots' not in st.session_state:
    st.session_state.dashboard_plots = []  # List of plot configs for dashboard

# ============ SIDEBAR ============
with st.sidebar:
    st.header("📁 Data Source")
    
    uploaded_file = st.file_uploader(
        "Upload your data",
        type=["csv", "xlsx", "xls", "parquet", "json"],
        help="Supports CSV, Excel, Parquet, JSON"
    )
    
    if uploaded_file is not None:
        try:
            name = uploaded_file.name.lower()
            if name.endswith('.csv'):
                df_loaded = pd.read_csv(uploaded_file)
            elif name.endswith(('.xlsx', '.xls')):
                df_loaded = pd.read_excel(uploaded_file)
            elif name.endswith('.parquet'):
                df_loaded = pd.read_parquet(uploaded_file)
            elif name.endswith('.json'):
                df_loaded = pd.read_json(uploaded_file)
            else:
                df_loaded = None
            
            if df_loaded is not None and not df_loaded.empty:
                # Better processing for uploaded files (fixes many editing issues)
                df_loaded = df_loaded.reset_index(drop=True)
                df_loaded.columns = [str(c).strip() for c in df_loaded.columns]
                
                # Try to auto-convert obvious datetime columns
                for col in df_loaded.columns:
                    if df_loaded[col].dtype == 'object':
                        try:
                            converted = pd.to_datetime(df_loaded[col], errors='coerce')
                            if converted.notna().sum() > len(df_loaded) * 0.5:  # if >50% converted successfully
                                df_loaded[col] = converted
                        except:
                            pass
                
                st.session_state.df = df_loaded.copy()
                st.session_state.original_df = df_loaded.copy()
                st.success(f"✅ Loaded {df_loaded.shape[0]:,} rows × {df_loaded.shape[1]} cols")
            else:
                st.error("File loaded but appears empty.")
        except Exception as e:
            st.error(f"Load error: {str(e)}")
    
    st.divider()
    st.subheader("🎮 Try Demo Data")
    
    demo_btns = st.columns(3)
    demo_datasets = {
        "Iris": px.data.iris,
        "Tips": px.data.tips,
        "Gapminder": px.data.gapminder,
        
        "Wind": px.data.wind,
        "Stocks": px.data.stocks
    }
    
    btn_keys = list(demo_datasets.keys())
    for idx, name in enumerate(btn_keys):
        col = demo_btns[idx % 3]
        if col.button(name, key=f"demo_{name}", use_container_width=True):
            st.session_state.df = demo_datasets[name]().copy()
            st.session_state.original_df = st.session_state.df.copy()
            st.rerun()
    
    if st.button("🗑️ Clear Everything", type="secondary", use_container_width=True):
        for key in ['df', 'original_df', 'last_fig', 'plot_config', 'plot_type']:
            if key in st.session_state:
                st.session_state[key] = None
        st.rerun()

# ============ MAIN ============
if st.session_state.df is None or st.session_state.df.empty:
    st.info("👈 Upload a file from the sidebar or click a demo dataset button to begin.")
    st.stop()

# Working dataframe (fresh copy each rerun)
working_df = st.session_state.df.copy()

# ============ TABS ============
tab_data, tab_config, tab_viz, tab_dashboard = st.tabs([
    "📋 Data Preview & Edit", 
    "🎨 Plot Configuration", 
    "📈 Visualize & Download",
    "📊 Dashboard"
])

# ---------- TAB 1: DATA ----------
with tab_data:
    st.subheader("✏️ Interactive Data Editor")
    st.caption("Edit values, add or remove rows directly. Click **Apply Changes** when done.")
    
    # Data editor (compatible with older Streamlit versions)
    edited_df = st.data_editor(
        working_df,
        key="main_data_editor",
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True
    )
    
    btn_col1, btn_col2, btn_col3 = st.columns([1.1, 1.1, 1.1])
    with btn_col1:
        if st.button("💾 Apply Edits", type="primary", use_container_width=True):
            st.session_state.df = edited_df.copy()
            st.success("Data updated successfully!")
            st.rerun()
    
    with btn_col2:
        if st.button("↩️ Reset to Original", use_container_width=True):
            if st.session_state.original_df is not None:
                st.session_state.df = st.session_state.original_df.copy()
                st.info("Reset to original data.")
                st.rerun()
    
    with btn_col3:
        if st.button("🔄 Refresh Table", use_container_width=True):
            st.rerun()
    
    st.divider()
    
    # ====================== BULK ROW DELETION (Compatible method) ======================
    with st.expander("🗑️ Bulk Delete Rows (works on older Streamlit)", expanded=False):
        st.caption("This method works even on older versions of Streamlit that don't support row selection in the table.")
        
        if st.button("Enable row selection for bulk delete"):
            # Add a temporary selection column
            if "__select_to_delete__" not in st.session_state.df.columns:
                st.session_state.df["__select_to_delete__"] = False
            st.success("Selection column added. Check the boxes in the '__select_to_delete__' column for rows you want to delete, then click 'Delete Selected Rows' below.")
            st.rerun()
        
        if "__select_to_delete__" in st.session_state.df.columns:
            if st.button("🗑️ Delete Selected Rows", type="secondary"):
                try:
                    mask = st.session_state.df["__select_to_delete__"] == True
                    num_deleted = int(mask.sum())
                    
                    if num_deleted > 0:
                        st.session_state.df = st.session_state.df[~mask].copy()
                        # Remove the temporary column
                        if "__select_to_delete__" in st.session_state.df.columns:
                            st.session_state.df = st.session_state.df.drop(columns=["__select_to_delete__"])
                        
                        st.success(f"Deleted {num_deleted} row(s).")
                        st.rerun()
                    else:
                        st.warning("No rows were selected (no checkboxes checked).")
                except Exception as e:
                    st.error(f"Error during deletion: {e}")
            
            if st.button("Cancel / Remove selection column"):
                if "__select_to_delete__" in st.session_state.df.columns:
                    st.session_state.df = st.session_state.df.drop(columns=["__select_to_delete__"])
                st.info("Selection column removed.")
                st.rerun()
    
    st.divider()

    # ====================== COLUMN TOOLS (Add / Delete) ======================
    with st.expander("➕ Add / Delete Columns", expanded=True):
        st.caption("**Note:** Changes are applied immediately. If the new column doesn't appear right away, click the **'Apply Edits'** button above the table once.")
        
        col1, col2 = st.columns(2)
        
        # --- ADD COLUMN ---
        with col1:
            st.markdown("**Add New Column**")
            new_col_name = st.text_input("Column name", placeholder="e.g. Region, Score", key="new_col_name")
            col_type = st.selectbox("Type", ["Text", "Number", "True/False"], key="new_col_type")
            
            default_val = ""
            if col_type == "Number":
                default_val = st.number_input("Default value", value=0.0, key="new_col_default_num")
            elif col_type == "True/False":
                default_val = st.selectbox("Default value", [True, False], key="new_col_default_bool")
            else:
                default_val = st.text_input("Default value (optional)", value="", key="new_col_default_text")
            
            if st.button("Add Column", type="primary", key="btn_add_col"):
                if not new_col_name or new_col_name.strip() == "":
                    st.error("Column name cannot be empty.")
                elif new_col_name in st.session_state.df.columns:
                    st.error("A column with this name already exists.")
                else:
                    if col_type == "Text":
                        st.session_state.df[new_col_name] = str(default_val) if default_val else ""
                    elif col_type == "Number":
                        st.session_state.df[new_col_name] = float(default_val)
                    else:
                        st.session_state.df[new_col_name] = bool(default_val)
                    
                    st.success(f"✅ Column '{new_col_name}' added successfully!")
                    st.rerun()
        
        # --- DELETE COLUMN ---
        with col2:
            st.markdown("**Delete Column**")
            cols_to_delete = [c for c in st.session_state.df.columns]
            col_to_delete = st.selectbox("Select column to delete", cols_to_delete, key="col_to_delete")
            
            if st.button("Delete Selected Column", type="secondary", key="btn_del_col"):
                if col_to_delete in st.session_state.df.columns:
                    st.session_state.df = st.session_state.df.drop(columns=[col_to_delete])
                    st.success(f"✅ Column '{col_to_delete}' deleted.")
                    st.rerun()
                else:
                    st.error("Column not found.")
    
    with st.expander("🧹 Quick Cleaning & Summary Tools", expanded=False):
        s1, s2 = st.columns([1, 1])
        with s1:
            st.metric("Rows", f"{working_df.shape[0]:,}")
            st.metric("Columns", working_df.shape[1])
            st.metric("Missing cells", int(working_df.isna().sum().sum()))
        
        with s2:
            if st.button("Drop rows with any missing values"):
                st.session_state.df = working_df.dropna().copy()
                st.success("Missing rows removed.")
                st.rerun()
            
            if st.button("Fill numeric NaNs with column median"):
                num_cols = working_df.select_dtypes(include=np.number).columns.tolist()
                for c in num_cols:
                    if working_df[c].isna().any():
                        working_df[c] = working_df[c].fillna(working_df[c].median())
                st.session_state.df = working_df.copy()
                st.success("Numeric missing values filled with median.")
                st.rerun()
        
        st.write("**Column Overview**")
        overview = pd.DataFrame({
            "Column": working_df.columns,
            "Type": working_df.dtypes.astype(str),
            "Non-Null Count": working_df.count().values,
            "Unique Values": working_df.nunique().values,
            "% Missing": (working_df.isna().mean() * 100).round(1).values
        })
        st.dataframe(overview, use_container_width=True, hide_index=True)

# ---------- TAB 2: CONFIG ----------
with tab_config:
    st.subheader("🎨 Configure Your Plot")
    
    all_cols = list(working_df.columns)
    num_cols = [c for c in all_cols if pd.api.types.is_numeric_dtype(working_df[c])]
    cat_cols = [c for c in all_cols if not pd.api.types.is_numeric_dtype(working_df[c])]
    
    plot_type = st.selectbox(
        "Choose Plot Type",
        [
            "Scatter Plot", "Line Plot", "Bar Chart", "Histogram",
            "Box Plot", "Violin Plot", "Density Heatmap",
            "Pie Chart", "Sunburst Chart", "Treemap", "Scatter Matrix"
        ],
        index=0
    )
    
    # Basic layout
    c1, c2 = st.columns(2)
    with c1:
        title = st.text_input("Plot Title", value=f"{plot_type}")
        height = st.slider("Height (px)", 450, 1200, 680, 25)
    with c2:
        width = st.slider("Width (px)", 600, 1600, 980, 25)
        template = st.selectbox("Theme", ["plotly", "plotly_dark", "ggplot2", "seaborn", "simple_white", "presentation"], index=0)
    
    st.markdown("### 📐 Faceting")
    facet_style = st.radio(
        "Faceting mode",
        ["None", "Facet Wrap (recommended for many categories)", "Facet Grid (row × col)"],
        horizontal=True,
        help="Facet Wrap automatically arranges many subplots in a grid. Facet Grid lets you choose row and column variables separately."
    )
    
    facet_col = None
    facet_row = None
    facet_wrap_col = None
    facet_col_wrap = 3
    
    if facet_style == "Facet Wrap (recommended for many categories)":
        facet_wrap_col = st.selectbox("Wrap using column", [None] + all_cols, index=0)
        facet_col_wrap = st.slider("Max columns before wrapping to next row", 1, 6, 3)
    elif facet_style == "Facet Grid (row × col)":
        facet_col = st.selectbox("Columns (horizontal split)", [None] + all_cols, index=0)
        facet_row = st.selectbox("Rows (vertical split)", [None] + all_cols, index=0)
    
    st.markdown("### 🎨 Color, Symbol & Size")
    color_col = st.selectbox("Color by", [None] + all_cols, index=0)
    symbol_col = None
    size_col = None
    
    if plot_type in ["Scatter Plot", "Scatter Matrix"]:
        symbol_col = st.selectbox("Symbol by (categorical)", [None] + cat_cols, index=0)
        if plot_type == "Scatter Plot":
            size_col = st.selectbox("Size by (bubble chart)", [None] + num_cols, index=0)
    
    st.markdown("### 📍 Main Variables")
    
    x_col = y_col = names_col = values_col = path_cols = dimensions = nbins = z_col = None
    trendline = marginal_x = marginal_y = barmode = None
    multiple_y_cols = None
    
    # Scatter, Box, Violin - single Y only
    if plot_type in ["Scatter Plot", "Box Plot", "Violin Plot"]:
        x_col = st.selectbox("X variable", all_cols, index=0)
        y_col = st.selectbox("Y variable", [None] + all_cols, index=1 if len(all_cols) > 1 else 0)
    
    # Line Chart - support multiple Y (multiple lines)
    elif plot_type == "Line Plot":
        x_col = st.selectbox("X variable", all_cols, index=0)
        use_multiple_y = st.checkbox("Use multiple Y variables (multiple lines)", value=False)
        
        if use_multiple_y:
            multiple_y_cols = st.multiselect(
                "Select multiple Y variables",
                num_cols if num_cols else all_cols,
                default=num_cols[:min(4, len(num_cols))] if num_cols else []
            )
            y_col = None
            st.caption("This will plot multiple lines (one per Y variable).")
        else:
            y_col = st.selectbox("Y variable", [None] + all_cols, index=1 if len(all_cols) > 1 else 0)
    
    # Bar Chart - support multiple Y (grouped bars)
    elif plot_type == "Bar Chart":
        x_col = st.selectbox("X variable", all_cols, index=0)
        use_multiple_y = st.checkbox("Use multiple Y variables (grouped bars)", value=False)
        
        if use_multiple_y:
            multiple_y_cols = st.multiselect(
                "Select multiple Y variables",
                num_cols if num_cols else all_cols,
                default=num_cols[:min(4, len(num_cols))] if num_cols else []
            )
            y_col = None
            st.caption("This will create grouped bars for each selected Y variable.")
        else:
            y_col = st.selectbox("Y variable", [None] + all_cols, index=1 if len(all_cols) > 1 else 0)
    
    elif plot_type == "Histogram":
        x_col = st.selectbox("Variable to plot", num_cols if num_cols else all_cols, index=0)
        nbins = st.slider("Number of bins", 5, 80, 20)
    elif plot_type == "Density Heatmap":
        x_col = st.selectbox("X (numeric)", num_cols if num_cols else all_cols, index=0)
        y_col = st.selectbox("Y (numeric)", num_cols if num_cols else all_cols, index=min(1, len(num_cols)-1) if num_cols else 0)
        z_col = st.selectbox("Intensity (optional numeric)", [None] + num_cols, index=0)
    elif plot_type == "Pie Chart":
        names_col = st.selectbox("Slice labels (categories)", cat_cols if cat_cols else all_cols, index=0)
        values_col = st.selectbox("Slice sizes (numeric)", num_cols if num_cols else all_cols, index=0)
    elif plot_type in ["Sunburst Chart", "Treemap"]:
        path_cols = st.multiselect(
            "Hierarchy path (order matters: e.g. Region → Country → City)",
            all_cols,
            default=all_cols[:min(3, len(all_cols))]
        )
        values_col = st.selectbox("Size / Value column", num_cols if num_cols else all_cols, index=0)
    elif plot_type == "Scatter Matrix":
        dimensions = st.multiselect(
            "Include these variables (3–6 recommended)",
            num_cols if num_cols else all_cols,
            default=(num_cols[:min(5, len(num_cols))] if num_cols else all_cols[:min(5, len(all_cols))])
        )
    
    # Advanced panel
    with st.expander("⚙️ Advanced Options & Styling"):
        adv1, adv2 = st.columns(2)
        with adv1:
            log_x = st.checkbox("Logarithmic X axis", value=False)
            log_y = st.checkbox("Logarithmic Y axis", value=False)
            show_legend = st.checkbox("Show legend", value=True)
            legend_pos = st.selectbox("Legend position", ["right", "bottom", "top", "left"], index=0)
        
        with adv2:
            opacity = st.slider("Opacity", 0.2, 1.0, 0.85, 0.05)
            base_marker_size = st.slider("Base marker size (scatter)", 3, 18, 7)
            
            if plot_type == "Scatter Plot":
                trendline = st.selectbox("Trendline", [None, "ols", "lowess"], index=0)
                marginal_x = st.selectbox("Marginal X", [None, "histogram", "violin", "box"], index=0)
                marginal_y = st.selectbox("Marginal Y", [None, "histogram", "violin", "box"], index=0)
            
            if plot_type in ["Box Plot", "Violin Plot"]:
                points_option = st.selectbox("Show points / outliers", 
                                             ["outliers", "all", False], index=0,
                                             help="'outliers' shows only outliers, 'all' shows every point")
            
            if plot_type == "Bar Chart":
                barmode = st.selectbox("Bar grouping", ["group", "stack", "relative"], index=0, 
                                       help="Use 'group' for grouped/side-by-side bars (requires a 'Color by' column)")
        
        x_label = st.text_input("Custom X-axis label (optional)", value="")
        y_label = st.text_input("Custom Y-axis label (optional)", value="")
        
        color_scale = st.selectbox(
            "Color palette / scale",
            ["Viridis", "Plasma", "Inferno", "Magma", "Cividis", "Turbo", "RdBu", "Spectral", "Set1", "Set2", "Paired", "Dark2"],
            index=0
        )
    
    # Save config to session
    st.session_state.plot_config = {
        "plot_type": plot_type,
        "title": title,
        "height": height,
        "width": width,
        "template": template,
        "facet_col": facet_col,
        "facet_row": facet_row,
        "facet_wrap_col": facet_wrap_col,
        "facet_col_wrap": facet_col_wrap,
        "color": color_col,
        "symbol": symbol_col,
        "size": size_col,
        "x": x_col,
        "y": y_col,
        "multiple_y": multiple_y_cols,
        "names": names_col,
        "values": values_col,
        "path": path_cols,
        "dimensions": dimensions,
        "nbins": nbins,
        "z": z_col,
        "trendline": trendline,
        "marginal_x": marginal_x,
        "marginal_y": marginal_y,
        "barmode": barmode,
        "log_x": log_x,
        "log_y": log_y,
        "show_legend": show_legend,
        "legend_pos": legend_pos,
        "opacity": opacity,
        "marker_size": base_marker_size,
        "x_label": x_label,
        "y_label": y_label,
        "color_scale": color_scale
    }
    st.session_state.plot_type = plot_type

# ---------- TAB 3: VIZ & DOWNLOAD ----------
with tab_viz:
    st.subheader("📈 Interactive Preview")
    
    gen_btn = st.button("🚀 Generate Plot", type="primary", use_container_width=True)
    
    if gen_btn:
        cfg = st.session_state.plot_config
        ptype = cfg.get("plot_type")
        df_plot = st.session_state.df.copy()
        
        if df_plot is None or df_plot.empty:
            st.error("No data to plot.")
        else:
            try:
                labels = {}
                if cfg.get("x_label"): labels[cfg.get("x", "")] = cfg["x_label"]
                if cfg.get("y_label"): labels[cfg.get("y", "")] = cfg["y_label"]
                
                base_kwargs = {
                    "title": cfg.get("title", ""),
                    "height": cfg.get("height", 680),
                    "width": cfg.get("width", 980),
                    "template": cfg.get("template", "plotly"),
                    "labels": labels if labels else None,
                }
                
                # Facet handling
                facet_kwargs = {}
                if cfg.get("facet_col"):
                    facet_kwargs["facet_col"] = cfg["facet_col"]
                if cfg.get("facet_row"):
                    facet_kwargs["facet_row"] = cfg["facet_row"]
                if cfg.get("facet_wrap_col"):
                    facet_kwargs["facet_col"] = cfg["facet_wrap_col"]
                    facet_kwargs["facet_col_wrap"] = cfg.get("facet_col_wrap", 3)
                
                # Color handling (recompute numeric columns locally to avoid scope issues)
                df_plot_cols = df_plot.columns.tolist()
                num_cols_local = [c for c in df_plot_cols if pd.api.types.is_numeric_dtype(df_plot[c])]
                color_kwargs = {}
                if cfg.get("color"):
                    color_kwargs["color"] = cfg["color"]
                    cscale = cfg.get("color_scale", "Viridis")
                    
                    # Only apply continuous scale to plot types that support it
                    continuous_supported = ptype in ["Scatter Plot", "Bar Chart", "Histogram", 
                                                     "Box Plot", "Violin Plot", "Density Heatmap"]
                    
                    if cfg["color"] in num_cols_local and continuous_supported:
                        color_kwargs["color_continuous_scale"] = cscale.lower()
                    else:
                        # discrete palette (works for Line, Scatter, etc.)
                        pal = getattr(px.colors.qualitative, cscale, px.colors.qualitative.Plotly)
                        color_kwargs["color_discrete_sequence"] = pal
                
                fig = None
                
                if ptype == "Scatter Plot":
                    fig = px.scatter(
                        df_plot,
                        x=cfg.get("x"),
                        y=cfg.get("y"),
                        symbol=cfg.get("symbol"),
                        size=cfg.get("size"),
                        trendline=cfg.get("trendline"),
                        marginal_x=cfg.get("marginal_x"),
                        marginal_y=cfg.get("marginal_y"),
                        **base_kwargs,
                        **facet_kwargs,
                        **color_kwargs
                    )
                    if cfg.get("marker_size") and not cfg.get("size"):
                        fig.update_traces(marker=dict(size=cfg["marker_size"]))
                
                elif ptype == "Line Plot":
                    y_for_line = cfg.get("multiple_y") if cfg.get("multiple_y") else cfg.get("y")
                    fig = px.line(
                        df_plot,
                        x=cfg.get("x"),
                        y=y_for_line,
                        markers=True,
                        **base_kwargs,
                        **facet_kwargs,
                        **color_kwargs
                    )
                
                elif ptype == "Bar Chart":
                    y_for_bar = cfg.get("multiple_y") if cfg.get("multiple_y") else cfg.get("y")
                    fig = px.bar(
                        df_plot,
                        x=cfg.get("x"),
                        y=y_for_bar,
                        barmode=cfg.get("barmode", "group"),
                        **base_kwargs,
                        **facet_kwargs,
                        **color_kwargs
                    )
                
                elif ptype == "Histogram":
                    fig = px.histogram(
                        df_plot,
                        x=cfg.get("x"),
                        nbins=cfg.get("nbins", 20),
                        **base_kwargs,
                        **facet_kwargs,
                        **color_kwargs
                    )
                
                elif ptype == "Box Plot":
                    fig = px.box(
                        df_plot,
                        x=cfg.get("x"),
                        y=cfg.get("y"),
                        points="outliers",
                        **base_kwargs,
                        **facet_kwargs,
                        **color_kwargs
                    )
                
                elif ptype == "Violin Plot":
                    fig = px.violin(
                        df_plot,
                        x=cfg.get("x"),
                        y=cfg.get("y"),
                        box=True,
                        points="outliers",
                        **base_kwargs,
                        **facet_kwargs,
                        **color_kwargs
                    )
                
                elif ptype == "Density Heatmap":
                    fig = px.density_heatmap(
                        df_plot,
                        x=cfg.get("x"),
                        y=cfg.get("y"),
                        z=cfg.get("z"),
                        color_continuous_scale=cfg.get("color_scale", "Viridis").lower(),
                        **base_kwargs,
                        **facet_kwargs
                    )
                
                elif ptype == "Pie Chart":
                    fig = px.pie(
                        df_plot,
                        names=cfg.get("names"),
                        values=cfg.get("values"),
                        hole=0.35,
                        title=cfg.get("title"),
                        height=cfg.get("height"),
                        width=cfg.get("width"),
                        template=cfg.get("template")
                    )
                
                elif ptype == "Sunburst Chart":
                    fig = px.sunburst(
                        df_plot,
                        path=cfg.get("path", []),
                        values=cfg.get("values"),
                        color=cfg.get("color"),
                        title=cfg.get("title"),
                        height=cfg.get("height"),
                        width=cfg.get("width"),
                        template=cfg.get("template")
                    )
                
                elif ptype == "Treemap":
                    fig = px.treemap(
                        df_plot,
                        path=cfg.get("path", []),
                        values=cfg.get("values"),
                        color=cfg.get("color"),
                        title=cfg.get("title"),
                        height=cfg.get("height"),
                        width=cfg.get("width"),
                        template=cfg.get("template")
                    )
                
                elif ptype == "Scatter Matrix":
                    fig = px.scatter_matrix(
                        df_plot,
                        dimensions=cfg.get("dimensions", all_cols[:4]),
                        color=cfg.get("color"),
                        symbol=cfg.get("symbol"),
                        title=cfg.get("title"),
                        height=cfg.get("height"),
                        width=cfg.get("width"),
                        template=cfg.get("template")
                    )
                
                if fig is not None:
                    # Layout polish
                    legend_orient = "h" if cfg.get("legend_pos") in ["bottom", "top"] else "v"
                    fig.update_layout(
                        showlegend=cfg.get("show_legend", True),
                        legend=dict(
                            orientation=legend_orient,
                            yanchor="top" if legend_orient == "h" else "middle",
                            y=1.02 if legend_orient == "h" else 0.5,
                            xanchor="center" if legend_orient == "h" else "left",
                            x=0.5 if legend_orient == "h" else 1.02
                        )
                    )
                    
                    if cfg.get("log_x"):
                        fig.update_xaxes(type="log")
                    if cfg.get("log_y"):
                        fig.update_yaxes(type="log")
                    
                    if cfg.get("opacity") and ptype in ["Scatter Plot", "Line Plot", "Bar Chart"]:
                        fig.update_traces(marker=dict(opacity=cfg["opacity"]))
                    
                    st.session_state.last_fig = fig
                    st.success("✅ Plot ready!")

                    # Add to Dashboard button (Step 1 of advanced dashboard)
                    if st.button("➕ Add this plot to Dashboard", key="add_to_dashboard"):
                        plot_copy = st.session_state.plot_config.copy()
                        plot_copy["id"] = len(st.session_state.dashboard_plots) + 1
                        st.session_state.dashboard_plots.append(plot_copy)
                        st.success("Plot added to Dashboard! Go to the 📊 Dashboard tab to view it.")
                else:
                    st.warning("Plot type not fully implemented or missing required columns.")
            
            except Exception as err:
                st.error(f"Error while building plot: {err}")
                with st.expander("Technical traceback"):
                    st.exception(err)
    
    # Render plot if available
    if st.session_state.last_fig is not None:
        st.plotly_chart(
            st.session_state.last_fig,
            use_container_width=True,
            config={"displayModeBar": True, "displaylogo": False, "toImageButtonOptions": {"format": "png", "filename": "dataviz_studio_plot"}}
        )
        
        st.divider()
        st.subheader("⬇️ Export Options")
        
        d1, d2, d3 = st.columns(3)
        
        with d1:
            try:
                html_buf = BytesIO()
                st.session_state.last_fig.write_html(html_buf, include_plotlyjs="cdn", full_html=True)
                html_buf.seek(0)
                st.download_button(
                    "🌐 Download Interactive HTML",
                    data=html_buf.getvalue(),
                    file_name=f"plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    use_container_width=True,
                    help="Fully interactive plot. Open in any browser."
                )
            except Exception as e:
                st.caption(f"HTML export failed: {e}")
        
        with d2:
            try:
                png_buf = BytesIO()
                st.session_state.last_fig.write_image(png_buf, format="png", scale=2)
                png_buf.seek(0)
                st.download_button(
                    "🖼️ Download PNG (High Resolution)",
                    data=png_buf.getvalue(),
                    file_name=f"plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png",
                    use_container_width=True
                )
            except Exception as e:
                st.info("PNG export requires kaleido (may not be available here). HTML download or screenshot works great!")
        
        with d3:
            csv_buf = BytesIO()
            st.session_state.df.to_csv(csv_buf, index=False)
            csv_buf.seek(0)
            st.download_button(
                "📄 Download Current Data (CSV)",
                data=csv_buf.getvalue(),
                file_name=f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        st.caption("The HTML version is the most powerful — it preserves full interactivity for your audience.")

# ---------- TAB 4: DASHBOARD (Step 1) ----------
with tab_dashboard:
    st.subheader("📊 Dashboard Builder")
    st.caption("Combine multiple plots. Start by adding plots from the Visualize tab using the '➕ Add this plot to Dashboard' button.")

    if not st.session_state.dashboard_plots:
        st.info("No plots added yet. Create a plot in the **📈 Visualize & Download** tab and click **'➕ Add this plot to Dashboard'**.")
    else:
        # Layout control
        layout_cols = st.selectbox(
            "Dashboard Layout",
            options=[1, 2, 3],
            index=1,
            help="Number of columns to arrange the plots"
        )

        # Clear dashboard button
        if st.button("🗑️ Clear All Dashboard Plots"):
            st.session_state.dashboard_plots = []
            st.rerun()

        st.divider()

        # Render plots in grid
        cols = st.columns(layout_cols)
        
        for idx, plot_cfg in enumerate(st.session_state.dashboard_plots):
            col = cols[idx % layout_cols]
            
            with col:
                st.markdown(f"**Plot {plot_cfg.get('id', idx+1)}: {plot_cfg.get('title', 'Untitled')}**")
                
                # Re-generate the figure using stored config
                try:
                    # Use the current working data
                    current_df = st.session_state.df.copy() if st.session_state.df is not None else None
                    
                    if current_df is not None and not current_df.empty:
                        # Simplified re-rendering (we'll improve this in later steps)
                        fig = None
                        ptype = plot_cfg.get("plot_type")
                        
                        # Re-render all supported plot types in Dashboard
                        if ptype == "Bar Chart":
                            y_val = plot_cfg.get("multiple_y") if plot_cfg.get("multiple_y") else plot_cfg.get("y")
                            fig = px.bar(
                                current_df,
                                x=plot_cfg.get("x"),
                                y=y_val,
                                color=plot_cfg.get("color"),
                                barmode=plot_cfg.get("barmode", "group"),
                                title=plot_cfg.get("title"),
                                height=400
                            )
                        elif ptype == "Line Plot":
                            y_val = plot_cfg.get("multiple_y") if plot_cfg.get("multiple_y") else plot_cfg.get("y")
                            fig = px.line(
                                current_df,
                                x=plot_cfg.get("x"),
                                y=y_val,
                                color=plot_cfg.get("color"),
                                markers=True,
                                title=plot_cfg.get("title"),
                                height=400
                            )
                        elif ptype == "Scatter Plot":
                            fig = px.scatter(
                                current_df,
                                x=plot_cfg.get("x"),
                                y=plot_cfg.get("y"),
                                color=plot_cfg.get("color"),
                                title=plot_cfg.get("title"),
                                height=400
                            )
                        elif ptype == "Histogram":
                            fig = px.histogram(
                                current_df,
                                x=plot_cfg.get("x"),
                                color=plot_cfg.get("color"),
                                nbins=plot_cfg.get("nbins", 20),
                                title=plot_cfg.get("title"),
                                height=400
                            )
                        elif ptype == "Box Plot":
                            fig = px.box(
                                current_df,
                                x=plot_cfg.get("x"),
                                y=plot_cfg.get("y"),
                                color=plot_cfg.get("color"),
                                points="outliers",
                                title=plot_cfg.get("title"),
                                height=400
                            )
                        elif ptype == "Violin Plot":
                            fig = px.violin(
                                current_df,
                                x=plot_cfg.get("x"),
                                y=plot_cfg.get("y"),
                                color=plot_cfg.get("color"),
                                box=True,
                                points="outliers",
                                title=plot_cfg.get("title"),
                                height=400
                            )
                        elif ptype == "Density Heatmap":
                            fig = px.density_heatmap(
                                current_df,
                                x=plot_cfg.get("x"),
                                y=plot_cfg.get("y"),
                                title=plot_cfg.get("title"),
                                height=400
                            )
                        elif ptype == "Pie Chart":
                            fig = px.pie(
                                current_df,
                                names=plot_cfg.get("names"),
                                values=plot_cfg.get("values"),
                                title=plot_cfg.get("title"),
                                height=400
                            )
                        elif ptype == "Sunburst Chart":
                            fig = px.sunburst(
                                current_df,
                                path=plot_cfg.get("path", []),
                                values=plot_cfg.get("values"),
                                color=plot_cfg.get("color"),
                                title=plot_cfg.get("title"),
                                height=400
                            )
                        elif ptype == "Treemap":
                            fig = px.treemap(
                                current_df,
                                path=plot_cfg.get("path", []),
                                values=plot_cfg.get("values"),
                                color=plot_cfg.get("color"),
                                title=plot_cfg.get("title"),
                                height=400
                            )
                        elif ptype == "Scatter Matrix":
                            fig = px.scatter_matrix(
                                current_df,
                                dimensions=plot_cfg.get("dimensions", []),
                                color=plot_cfg.get("color"),
                                title=plot_cfg.get("title"),
                                height=500
                            )
                        else:
                            st.info(f"Preview for '{ptype}' is not yet supported in Dashboard.")
                        
                        if fig:
                            st.plotly_chart(fig, use_container_width=True, key=f"dash_plot_{idx}")
                    
                    # Remove button for this plot
                    if st.button(f"❌ Remove Plot {idx+1}", key=f"remove_{idx}"):
                        st.session_state.dashboard_plots.pop(idx)
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error rendering plot {idx+1}: {str(e)}")

# Footer
st.divider()
st.caption("DataViz Studio • Make beautiful visualizations without writing code • Powered by Plotly & Streamlit")


# Guard: If someone runs this file directly with `python app.py` instead of `streamlit run app.py`
if __name__ == "__main__" and not st.runtime.exists():
    print("\n" + "="*60)
    print("⚠️  You ran this file with plain Python.")
    print("✅  Correct way to start the app:")
    print("    streamlit run app.py")
    print("\nOr simply double-click the 'run_app.sh' (Linux/Mac) or 'run_app.bat' (Windows) file I provided.")
    print("="*60 + "\n")