import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
from plotly.subplots import make_subplots
import plotly.graph_objects as go
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

st.markdown("""
<style>
    .stButton > button { font-weight: 600; }
    .stDownloadButton > button { background-color: #0e7c7b; color: white; border: none; }
    .main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
</style>
""", unsafe_allow_html=True)

st.title("📊 DataViz Studio")
st.caption("Upload • Edit • Select Variables • Group & Aggregate • Multi-Y • Bar Width & Boundaries • Dashboard Download")

# Session state
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
    st.session_state.dashboard_plots = []
if 'editor_key' not in st.session_state:
    st.session_state.editor_key = 0

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
                df_loaded = df_loaded.reset_index(drop=True)
                df_loaded.columns = [str(c).strip() for c in df_loaded.columns]
               
                for col in df_loaded.columns:
                    if df_loaded[col].dtype == 'object':
                        try:
                            converted = pd.to_datetime(df_loaded[col], errors='coerce')
                            if converted.notna().sum() > len(df_loaded) * 0.5:
                                df_loaded[col] = converted
                        except:
                            pass
               
                st.session_state.df = df_loaded.copy()
                st.session_state.original_df = df_loaded.copy()
                st.session_state.editor_key += 1
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
   
    for idx, name in enumerate(demo_datasets.keys()):
        col = demo_btns[idx % 3]
        if col.button(name, key=f"demo_{name}", use_container_width=True):
            st.session_state.df = demo_datasets[name]().copy()
            st.session_state.original_df = st.session_state.df.copy()
            st.session_state.editor_key += 1
            st.rerun()
   
    if st.button("🗑️ Clear Everything", type="secondary", use_container_width=True):
        for key in ['df', 'original_df', 'last_fig', 'plot_config', 'plot_type']:
            if key in st.session_state:
                st.session_state[key] = None
        st.session_state.dashboard_plots = []
        st.session_state.editor_key = 0
        st.rerun()

# ============ MAIN ============
if st.session_state.df is None or st.session_state.df.empty:
    st.info("👈 Upload a file or click a demo dataset to begin.")
    st.stop()

working_df = st.session_state.df.copy()

tab_data, tab_config, tab_viz, tab_dashboard = st.tabs([
    "📋 Data Preview & Edit",
    "🎨 Plot Configuration",
    "📈 Visualize & Download",
    "📊 Dashboard"
])

# ---------- TAB 1: DATA ----------
with tab_data:
    st.subheader("✏️ Interactive Data Editor")
    st.caption("Edit cells / rows. **Click Apply Edits** to save changes permanently.")
   
    edited_df = st.data_editor(
        working_df,
        key=f"main_data_editor_{st.session_state.editor_key}",
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True
    )
   
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("💾 Apply Edits", type="primary", use_container_width=True):
            st.session_state.df = edited_df.copy()
            st.session_state.editor_key += 1
            st.success("✅ Data updated!")
            st.rerun()
    with c2:
        if st.button("↩️ Reset to Original", use_container_width=True):
            if st.session_state.original_df is not None:
                st.session_state.df = st.session_state.original_df.copy()
                st.session_state.editor_key += 1
                st.rerun()
    with c3:
        if st.button("🔄 Refresh Table", use_container_width=True):
            st.rerun()

    st.divider()

    # Bulk delete, Melt, Select Variables, Group By (same as previous version)
    with st.expander("🗑️ Bulk Delete Rows", expanded=False):
        if st.button("Enable row selection for bulk delete"):
            if "__select_to_delete__" not in st.session_state.df.columns:
                st.session_state.df["__select_to_delete__"] = False
            st.session_state.editor_key += 1
            st.rerun()
        if "__select_to_delete__" in st.session_state.df.columns:
            if st.button("🗑️ Delete Selected Rows", type="secondary"):
                mask = st.session_state.df["__select_to_delete__"] == True
                num = int(mask.sum())
                if num > 0:
                    st.session_state.df = st.session_state.df[~mask].drop(columns=["__select_to_delete__"], errors="ignore")
                    st.session_state.editor_key += 1
                    st.success(f"Deleted {num} rows")
                    st.rerun()
            if st.button("Cancel selection column"):
                st.session_state.df = st.session_state.df.drop(columns=["__select_to_delete__"], errors="ignore")
                st.session_state.editor_key += 1
                st.rerun()

    with st.expander("🔄 Melt Data for Multi-Metric Plotting", expanded=False):
        numeric_cols_for_melt = [c for c in st.session_state.df.columns if pd.api.types.is_numeric_dtype(st.session_state.df[c])]
        if len(numeric_cols_for_melt) >= 2:
            id_vars = st.multiselect("ID columns", [c for c in st.session_state.df.columns if c not in numeric_cols_for_melt])
            value_vars = st.multiselect("Metric columns to melt", numeric_cols_for_melt,
                                        default=numeric_cols_for_melt[:min(5, len(numeric_cols_for_melt))])
            if st.button("Melt Data", type="primary"):
                if value_vars:
                    melted = pd.melt(st.session_state.df, id_vars=id_vars or None,
                                     value_vars=value_vars, var_name="Metric", value_name="Value")
                    st.session_state.df = melted
                    st.session_state.editor_key += 1
                    st.success(f"Melted → {melted.shape}")
                    st.rerun()

    with st.expander("🔍 Select Variables to Keep", expanded=False):
        cols_to_keep = st.multiselect("Select columns to keep", list(st.session_state.df.columns),
                                      default=list(st.session_state.df.columns))
        if st.button("✅ Keep Only Selected", type="primary"):
            if cols_to_keep:
                st.session_state.df = st.session_state.df[cols_to_keep]
                st.session_state.editor_key += 1
                st.rerun()

    with st.expander("📊 Group By & Aggregate", expanded=False):
        group_by_cols = st.multiselect("Grouping variables", list(st.session_state.df.columns))
        num_cols = [c for c in st.session_state.df.columns if pd.api.types.is_numeric_dtype(st.session_state.df[c])]
        value_cols = st.multiselect("Numeric columns to aggregate", num_cols, default=num_cols[:5])
        agg_method = st.selectbox("Aggregation", ["mean", "sum", "median", "count", "min", "max", "std"])
        if st.button("🚀 Apply Group By", type="primary"):
            if group_by_cols:
                if agg_method == "count":
                    grouped = st.session_state.df.groupby(group_by_cols, as_index=False).size().rename(columns={"size": "count"})
                else:
                    grouped = st.session_state.df.groupby(group_by_cols, as_index=False).agg({c: agg_method for c in value_cols})
                st.session_state.df = grouped
                st.session_state.editor_key += 1
                st.success(f"Grouped → {grouped.shape}")
                st.rerun()

    with st.expander("➕ Add / Delete Columns", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            new_col_name = st.text_input("New column name")
            col_type = st.selectbox("Type", ["Text", "Number", "True/False"])
            if col_type == "Number":
                default_val = st.number_input("Default", value=0.0)
            elif col_type == "True/False":
                default_val = st.selectbox("Default", [True, False])
            else:
                default_val = st.text_input("Default", value="")
            if st.button("Add Column", type="primary"):
                if new_col_name and new_col_name not in st.session_state.df.columns:
                    if col_type == "Text":
                        st.session_state.df[new_col_name] = str(default_val)
                    elif col_type == "Number":
                        st.session_state.df[new_col_name] = float(default_val)
                    else:
                        st.session_state.df[new_col_name] = bool(default_val)
                    st.session_state.editor_key += 1
                    st.rerun()
        with col2:
            col_to_delete = st.selectbox("Column to delete", list(st.session_state.df.columns))
            if st.button("Delete Column", type="secondary"):
                st.session_state.df = st.session_state.df.drop(columns=[col_to_delete])
                st.session_state.editor_key += 1
                st.rerun()

    with st.expander("🧹 Quick Cleaning", expanded=False):
        st.metric("Rows", f"{working_df.shape[0]:,}")
        st.metric("Columns", working_df.shape[1])
        if st.button("Drop rows with missing values"):
            st.session_state.df = working_df.dropna()
            st.session_state.editor_key += 1
            st.rerun()
        if st.button("Fill numeric NaNs with median"):
            for c in working_df.select_dtypes(include=np.number).columns:
                working_df[c] = working_df[c].fillna(working_df[c].median())
            st.session_state.df = working_df
            st.session_state.editor_key += 1
            st.rerun()

# ---------- TAB 2: CONFIG ----------
with tab_config:
    st.subheader("🎨 Configure Your Plot")
   
    all_cols = list(working_df.columns)
    num_cols = [c for c in all_cols if pd.api.types.is_numeric_dtype(working_df[c])]
    cat_cols = [c for c in all_cols if not pd.api.types.is_numeric_dtype(working_df[c])]
   
    plot_type = st.selectbox(
        "Choose Plot Type",
        ["Scatter Plot", "Line Plot", "Bar Chart", "Histogram",
         "Box Plot", "Violin Plot", "Density Heatmap",
         "Pie Chart", "Sunburst Chart", "Treemap", "Scatter Matrix"],
        index=0
    )
   
    c1, c2 = st.columns(2)
    with c1:
        title = st.text_input("Plot Title", value=plot_type)
        height = st.slider("Height (px)", 450, 1200, 680, 25)
    with c2:
        width = st.slider("Width (px)", 600, 1600, 980, 25)
        template = st.selectbox("Theme", ["plotly", "plotly_dark", "ggplot2", "seaborn", "simple_white", "presentation"])
   
    # Faceting
    st.markdown("### 📐 Faceting")
    facet_style = st.radio("Faceting mode", ["None", "Facet Wrap", "Facet Grid"], horizontal=True)
    facet_col = facet_row = facet_wrap_col = None
    facet_col_wrap = 3
    if facet_style == "Facet Wrap":
        facet_wrap_col = st.selectbox("Wrap using column", [None] + all_cols)
        facet_col_wrap = st.slider("Max columns", 1, 6, 3)
    elif facet_style == "Facet Grid":
        facet_col = st.selectbox("Columns", [None] + all_cols)
        facet_row = st.selectbox("Rows", [None] + all_cols)
   
    # Color / Symbol / Size
    st.markdown("### 🎨 Color, Symbol & Size")
    color_col = st.selectbox("Color by", [None] + all_cols)
    symbol_col = size_col = None
    if plot_type in ["Scatter Plot", "Scatter Matrix"]:
        symbol_col = st.selectbox("Symbol by", [None] + cat_cols)
        if plot_type == "Scatter Plot":
            size_col = st.selectbox("Size by (bubble)", [None] + num_cols)
   
    # ========== MAIN VARIABLES + MULTIPLE Y ==========
    st.markdown("### 📍 Main Variables")
   
    x_col = y_col = names_col = values_col = path_cols = dimensions = nbins = z_col = None
    trendline = marginal_x = marginal_y = barmode = None
    multiple_y_cols = None
    bar_width = 0.7
    show_boundaries = False
   
    # Plots that support multiple Y
    multi_y_supported = plot_type in ["Scatter Plot", "Line Plot", "Bar Chart", "Box Plot", "Violin Plot", "Histogram"]
   
    if multi_y_supported:
        use_multiple_y = st.checkbox("Use multiple Y variables", value=False,
                                     help="Plot several numeric columns at once (overlaid or grouped)")
        if use_multiple_y:
            multiple_y_cols = st.multiselect(
                "Select multiple Y variables",
                num_cols if num_cols else all_cols,
                default=num_cols[:min(4, len(num_cols))] if num_cols else []
            )
            y_col = None
        else:
            if plot_type == "Histogram":
                x_col = st.selectbox("Variable to plot", num_cols if num_cols else all_cols)
                nbins = st.slider("Number of bins", 5, 80, 20)
            else:
                x_col = st.selectbox("X variable", all_cols)
                y_col = st.selectbox("Y variable", [None] + all_cols, index=1 if len(all_cols) > 1 else 0)
    else:
        # Non multi-Y plots
        if plot_type == "Density Heatmap":
            x_col = st.selectbox("X (numeric)", num_cols if num_cols else all_cols)
            y_col = st.selectbox("Y (numeric)", num_cols if num_cols else all_cols, index=min(1, len(num_cols)-1) if num_cols else 0)
            z_col = st.selectbox("Intensity (optional)", [None] + num_cols)
        elif plot_type == "Pie Chart":
            names_col = st.selectbox("Slice labels", cat_cols if cat_cols else all_cols)
            values_col = st.selectbox("Slice sizes", num_cols if num_cols else all_cols)
        elif plot_type in ["Sunburst Chart", "Treemap"]:
            path_cols = st.multiselect("Hierarchy path", all_cols, default=all_cols[:min(3, len(all_cols))])
            values_col = st.selectbox("Size / Value", num_cols if num_cols else all_cols)
        elif plot_type == "Scatter Matrix":
            dimensions = st.multiselect("Variables (3–6 recommended)", num_cols if num_cols else all_cols,
                                        default=num_cols[:min(5, len(num_cols))] if num_cols else all_cols[:5])
   
    # Advanced
    with st.expander("⚙️ Advanced Options & Styling", expanded=True):
        adv1, adv2 = st.columns(2)
        with adv1:
            log_x = st.checkbox("Log X axis")
            log_y = st.checkbox("Log Y axis")
            show_legend = st.checkbox("Show legend", value=True)
            legend_pos = st.selectbox("Legend position", ["right", "bottom", "top", "left"])
        with adv2:
            opacity = st.slider("Opacity", 0.2, 1.0, 0.85, 0.05)
            base_marker_size = st.slider("Marker size (scatter)", 3, 18, 7)
           
            if plot_type == "Scatter Plot":
                trendline = st.selectbox("Trendline", [None, "ols", "lowess"])
                marginal_x = st.selectbox("Marginal X", [None, "histogram", "violin", "box"])
                marginal_y = st.selectbox("Marginal Y", [None, "histogram", "violin", "box"])
           
            if plot_type in ["Box Plot", "Violin Plot"]:
                points_option = st.selectbox("Show points", ["outliers", "all", False])
           
            if plot_type == "Bar Chart":
                barmode = st.selectbox("Bar grouping", ["group", "stack", "relative"])
                # NEW: Bar width + boundaries
                bar_width = st.slider("Bar width", 0.15, 1.0, 0.7, 0.05,
                                      help="1.0 = bars touch each other, lower = more gap")
                show_boundaries = st.checkbox("Show boundaries between categories",
                                              help="Draws vertical separator lines between x-axis groups")
       
        x_label = st.text_input("Custom X-axis label", value="")
        y_label = st.text_input("Custom Y-axis label", value="")
        color_scale = st.selectbox("Color scale", 
            ["Viridis", "Plasma", "Inferno", "Magma", "Cividis", "Turbo", "RdBu", "Spectral", "Set1", "Set2", "Paired", "Dark2"])
   
    # Save config
    st.session_state.plot_config = {
        "plot_type": plot_type, "title": title, "height": height, "width": width, "template": template,
        "facet_col": facet_col, "facet_row": facet_row, "facet_wrap_col": facet_wrap_col, "facet_col_wrap": facet_col_wrap,
        "color": color_col, "symbol": symbol_col, "size": size_col,
        "x": x_col, "y": y_col, "multiple_y": multiple_y_cols,
        "names": names_col, "values": values_col, "path": path_cols, "dimensions": dimensions,
        "nbins": nbins, "z": z_col, "trendline": trendline, "marginal_x": marginal_x, "marginal_y": marginal_y,
        "barmode": barmode, "bar_width": bar_width, "show_boundaries": show_boundaries,
        "log_x": log_x, "log_y": log_y, "show_legend": show_legend, "legend_pos": legend_pos,
        "opacity": opacity, "marker_size": base_marker_size,
        "x_label": x_label, "y_label": y_label, "color_scale": color_scale
    }
    st.session_state.plot_type = plot_type

# ---------- TAB 3: VIZ ----------
with tab_viz:
    st.subheader("📈 Interactive Preview")
   
    if st.button("🚀 Generate Plot", type="primary", use_container_width=True):
        cfg = st.session_state.plot_config
        ptype = cfg.get("plot_type")
        df_plot = st.session_state.df.copy()
       
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
           
            facet_kwargs = {}
            if cfg.get("facet_col"): facet_kwargs["facet_col"] = cfg["facet_col"]
            if cfg.get("facet_row"): facet_kwargs["facet_row"] = cfg["facet_row"]
            if cfg.get("facet_wrap_col"):
                facet_kwargs["facet_col"] = cfg["facet_wrap_col"]
                facet_kwargs["facet_col_wrap"] = cfg.get("facet_col_wrap", 3)
           
            color_kwargs = {}
            if cfg.get("color"):
                color_kwargs["color"] = cfg["color"]
                cscale = cfg.get("color_scale", "Viridis")
                num_local = [c for c in df_plot.columns if pd.api.types.is_numeric_dtype(df_plot[c])]
                if cfg["color"] in num_local and ptype in ["Scatter Plot", "Bar Chart", "Histogram", "Box Plot", "Violin Plot", "Density Heatmap"]:
                    color_kwargs["color_continuous_scale"] = cscale.lower()
                else:
                    pal = getattr(px.colors.qualitative, cscale, px.colors.qualitative.Plotly)
                    color_kwargs["color_discrete_sequence"] = pal
           
            fig = None
            y_data = cfg.get("multiple_y") if cfg.get("multiple_y") else cfg.get("y")
           
            if ptype == "Scatter Plot":
                fig = px.scatter(df_plot, x=cfg.get("x"), y=y_data,
                                 symbol=cfg.get("symbol"), size=cfg.get("size"),
                                 trendline=cfg.get("trendline"),
                                 marginal_x=cfg.get("marginal_x"), marginal_y=cfg.get("marginal_y"),
                                 **base_kwargs, **facet_kwargs, **color_kwargs)
                if cfg.get("marker_size") and not cfg.get("size"):
                    fig.update_traces(marker=dict(size=cfg["marker_size"]))
           
            elif ptype == "Line Plot":
                fig = px.line(df_plot, x=cfg.get("x"), y=y_data, markers=True,
                              **base_kwargs, **facet_kwargs, **color_kwargs)
           
            elif ptype == "Bar Chart":
                fig = px.bar(df_plot, x=cfg.get("x"), y=y_data,
                             barmode=cfg.get("barmode", "group"),
                             **base_kwargs, **facet_kwargs, **color_kwargs)
                # Apply bar width
                if cfg.get("bar_width"):
                    fig.update_traces(width=cfg["bar_width"])
                # Boundaries between categories
                if cfg.get("show_boundaries"):
                    fig.update_xaxes(showgrid=True, gridwidth=1.8, gridcolor="rgba(80,80,80,0.45)")
                    fig.update_layout(bargap=0.15)
           
            elif ptype == "Histogram":
                fig = px.histogram(df_plot, x=cfg.get("x") if not cfg.get("multiple_y") else None,
                                   y=y_data if cfg.get("multiple_y") else None,
                                   nbins=cfg.get("nbins", 20),
                                   **base_kwargs, **facet_kwargs, **color_kwargs)
           
            elif ptype == "Box Plot":
                fig = px.box(df_plot, x=cfg.get("x"), y=y_data, points="outliers",
                             **base_kwargs, **facet_kwargs, **color_kwargs)
           
            elif ptype == "Violin Plot":
                fig = px.violin(df_plot, x=cfg.get("x"), y=y_data, box=True, points="outliers",
                                **base_kwargs, **facet_kwargs, **color_kwargs)
           
            elif ptype == "Density Heatmap":
                fig = px.density_heatmap(df_plot, x=cfg.get("x"), y=cfg.get("y"), z=cfg.get("z"),
                                         color_continuous_scale=cfg.get("color_scale", "Viridis").lower(),
                                         **base_kwargs, **facet_kwargs)
           
            elif ptype == "Pie Chart":
                fig = px.pie(df_plot, names=cfg.get("names"), values=cfg.get("values"),
                             hole=0.35, title=cfg.get("title"),
                             height=cfg.get("height"), width=cfg.get("width"), template=cfg.get("template"))
           
            elif ptype == "Sunburst Chart":
                fig = px.sunburst(df_plot, path=cfg.get("path", []), values=cfg.get("values"),
                                  color=cfg.get("color"), title=cfg.get("title"),
                                  height=cfg.get("height"), width=cfg.get("width"), template=cfg.get("template"))
           
            elif ptype == "Treemap":
                fig = px.treemap(df_plot, path=cfg.get("path", []), values=cfg.get("values"),
                                 color=cfg.get("color"), title=cfg.get("title"),
                                 height=cfg.get("height"), width=cfg.get("width"), template=cfg.get("template"))
           
            elif ptype == "Scatter Matrix":
                fig = px.scatter_matrix(df_plot, dimensions=cfg.get("dimensions", all_cols[:4]),
                                        color=cfg.get("color"), symbol=cfg.get("symbol"),
                                        title=cfg.get("title"), height=cfg.get("height"),
                                        width=cfg.get("width"), template=cfg.get("template"))
           
            if fig is not None:
                legend_orient = "h" if cfg.get("legend_pos") in ["bottom", "top"] else "v"
                fig.update_layout(
                    showlegend=cfg.get("show_legend", True),
                    legend=dict(orientation=legend_orient,
                                yanchor="top" if legend_orient == "h" else "middle",
                                y=1.02 if legend_orient == "h" else 0.5,
                                xanchor="center" if legend_orient == "h" else "left",
                                x=0.5 if legend_orient == "h" else 1.02)
                )
                if cfg.get("log_x"): fig.update_xaxes(type="log")
                if cfg.get("log_y"): fig.update_yaxes(type="log")
                if cfg.get("opacity") and ptype in ["Scatter Plot", "Line Plot", "Bar Chart"]:
                    fig.update_traces(marker=dict(opacity=cfg["opacity"]))
               
                st.session_state.last_fig = fig
                st.success("✅ Plot ready!")
       
        except Exception as err:
            st.error(f"Error: {err}")
            with st.expander("Traceback"):
                st.exception(err)
   
    # Show plot + Add to Dashboard
    if st.session_state.last_fig is not None:
        st.plotly_chart(st.session_state.last_fig, use_container_width=True,
                        config={"displayModeBar": True, "displaylogo": False})
       
        if st.button("➕ Add this plot to Dashboard", key="add_to_dashboard"):
            plot_copy = st.session_state.plot_config.copy()
            plot_copy["id"] = len(st.session_state.dashboard_plots) + 1
            st.session_state.dashboard_plots.append(plot_copy)
            st.success(f"Added! Dashboard now has {len(st.session_state.dashboard_plots)} plot(s)")
            st.rerun()
       
        st.divider()
        st.subheader("⬇️ Export Options")
        d1, d2, d3 = st.columns(3)
        with d1:
            try:
                buf = BytesIO()
                st.session_state.last_fig.write_html(buf, include_plotlyjs="cdn", full_html=True)
                buf.seek(0)
                st.download_button("🌐 Interactive HTML", buf.getvalue(),
                                   f"plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html", "text/html",
                                   use_container_width=True)
            except: pass
        with d2:
            try:
                buf = BytesIO()
                st.session_state.last_fig.write_image(buf, format="png", scale=2)
                buf.seek(0)
                st.download_button("🖼️ High-res PNG", buf.getvalue(),
                                   f"plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png", "image/png",
                                   use_container_width=True)
            except:
                st.info("PNG needs kaleido")
        with d3:
            buf = BytesIO()
            st.session_state.df.to_csv(buf, index=False)
            buf.seek(0)
            st.download_button("📄 Current Data (CSV)", buf.getvalue(),
                               f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv",
                               use_container_width=True)

# ---------- TAB 4: DASHBOARD ----------
with tab_dashboard:
    st.subheader("📊 Dashboard Builder")
   
    if not st.session_state.dashboard_plots:
        st.info("Generate a plot → click **➕ Add this plot to Dashboard**")
    else:
        layout_cols = st.selectbox("Layout columns", [1, 2, 3], index=1)
        
        col_a, col_b = st.columns([1, 3])
        with col_a:
            if st.button("🗑️ Clear All"):
                st.session_state.dashboard_plots = []
                st.rerun()
        
        st.divider()
        
        # Render plots
        cols = st.columns(layout_cols)
        generated_figs = []   # collect for download
        
        for idx, plot_cfg in enumerate(st.session_state.dashboard_plots):
            with cols[idx % layout_cols]:
                st.markdown(f"**{plot_cfg.get('title', f'Plot {idx+1}')}**")
                try:
                    current_df = st.session_state.df.copy()
                    ptype = plot_cfg.get("plot_type")
                    y_val = plot_cfg.get("multiple_y") if plot_cfg.get("multiple_y") else plot_cfg.get("y")
                    fig = None
                    
                    if ptype == "Bar Chart":
                        fig = px.bar(current_df, x=plot_cfg.get("x"), y=y_val, color=plot_cfg.get("color"),
                                     barmode=plot_cfg.get("barmode", "group"), title=plot_cfg.get("title"), height=380)
                        if plot_cfg.get("bar_width"):
                            fig.update_traces(width=plot_cfg["bar_width"])
                        if plot_cfg.get("show_boundaries"):
                            fig.update_xaxes(showgrid=True, gridwidth=1.5, gridcolor="rgba(80,80,80,0.4)")
                    elif ptype == "Line Plot":
                        fig = px.line(current_df, x=plot_cfg.get("x"), y=y_val, color=plot_cfg.get("color"),
                                      markers=True, title=plot_cfg.get("title"), height=380)
                    elif ptype == "Scatter Plot":
                        fig = px.scatter(current_df, x=plot_cfg.get("x"), y=y_val, color=plot_cfg.get("color"),
                                         title=plot_cfg.get("title"), height=380)
                    elif ptype == "Histogram":
                        fig = px.histogram(current_df, x=plot_cfg.get("x"), color=plot_cfg.get("color"),
                                           nbins=plot_cfg.get("nbins", 20), title=plot_cfg.get("title"), height=380)
                    elif ptype == "Box Plot":
                        fig = px.box(current_df, x=plot_cfg.get("x"), y=y_val, color=plot_cfg.get("color"),
                                     points="outliers", title=plot_cfg.get("title"), height=380)
                    elif ptype == "Violin Plot":
                        fig = px.violin(current_df, x=plot_cfg.get("x"), y=y_val, color=plot_cfg.get("color"),
                                        box=True, points="outliers", title=plot_cfg.get("title"), height=380)
                    elif ptype == "Pie Chart":
                        fig = px.pie(current_df, names=plot_cfg.get("names"), values=plot_cfg.get("values"),
                                     title=plot_cfg.get("title"), height=380)
                    elif ptype == "Sunburst Chart":
                        fig = px.sunburst(current_df, path=plot_cfg.get("path", []), values=plot_cfg.get("values"),
                                          color=plot_cfg.get("color"), title=plot_cfg.get("title"), height=380)
                    elif ptype == "Treemap":
                        fig = px.treemap(current_df, path=plot_cfg.get("path", []), values=plot_cfg.get("values"),
                                         color=plot_cfg.get("color"), title=plot_cfg.get("title"), height=380)
                    else:
                        st.info(f"{ptype} preview limited in dashboard")
                    
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, key=f"dash_{idx}")
                        generated_figs.append(fig)
                    
                    if st.button(f"❌ Remove", key=f"rm_{idx}"):
                        st.session_state.dashboard_plots.pop(idx)
                        st.rerun()
                except Exception as e:
                    st.error(str(e))
        
        # ========== DASHBOARD DOWNLOAD ==========
        st.divider()
        st.subheader("📥 Download Dashboard")
        
        if generated_figs:
            # Combined HTML (most reliable)
            try:
                html_parts = []
                for i, f in enumerate(generated_figs):
                    html_parts.append(f"<h3>Plot {i+1}</h3>")
                    html_parts.append(f.to_html(full_html=False, include_plotlyjs='cdn' if i == 0 else False))
                
                full_html = f"""
                <html><head><title>DataViz Studio Dashboard</title>
                <style>body{{font-family:Arial; margin:20px;}} h3{{margin-top:40px;}}</style>
                </head><body>
                <h1>DataViz Studio Dashboard</h1>
                <p>Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                {''.join(html_parts)}
                </body></html>
                """
                st.download_button(
                    "🌐 Download Dashboard as Interactive HTML",
                    data=full_html,
                    file_name=f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    use_container_width=True
                )
            except Exception as e:
                st.warning(f"HTML export issue: {e}")
            
            # Try PNG (combined)
            try:
                # Simple vertical stack using make_subplots
                n = len(generated_figs)
                combined = make_subplots(rows=n, cols=1, subplot_titles=[f"Plot {i+1}" for i in range(n)],
                                         vertical_spacing=0.08)
                for i, f in enumerate(generated_figs):
                    for trace in f.data:
                        combined.add_trace(trace, row=i+1, col=1)
                combined.update_layout(height=400 * n, showlegend=False, title_text="Dashboard")
                
                buf = BytesIO()
                combined.write_image(buf, format="png", scale=2)
                buf.seek(0)
                st.download_button(
                    "🖼️ Download Dashboard as PNG (High-res)",
                    data=buf.getvalue(),
                    file_name=f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png",
                    use_container_width=True
                )
            except Exception:
                st.info("PNG dashboard export requires the `kaleido` package. HTML download works without it.")

st.divider()
st.caption("DataViz Studio • Multi-Y support • Bar width & boundaries • Dashboard export")
