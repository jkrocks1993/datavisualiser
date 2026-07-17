import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from io import BytesIO
import numpy as np
from datetime import datetime

st.set_page_config(page_title="DataViz Studio", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stButton > button { font-weight: 600; }
    .stDownloadButton > button { background-color: #0e7c7b; color: white; border: none; }
    .main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

st.title("📊 DataViz Studio")
st.caption("Empty facets are now automatically hidden • Cleaner controls • Exact boundary placement")

# ---------- Session state ----------
for key in ['df', 'original_df', 'last_fig', 'plot_config', 'plot_type']:
    if key not in st.session_state:
        st.session_state[key] = None
if 'dashboard_plots' not in st.session_state:
    st.session_state.dashboard_plots = []
if 'editor_key' not in st.session_state:
    st.session_state.editor_key = 0

# ---------- SIDEBAR ----------
with st.sidebar:
    st.header("📁 Data Source")
    uploaded_file = st.file_uploader("Upload your data", type=["csv", "xlsx", "xls", "parquet", "json"])
    
    if uploaded_file is not None:
        try:
            name = uploaded_file.name.lower()
            if name.endswith('.csv'):
                df_loaded = pd.read_csv(uploaded_file)
            elif name.endswith(('.xlsx', '.xls')):
                df_loaded = pd.read_excel(uploaded_file)
            elif name.endswith('.parquet'):
                df_loaded = pd.read_parquet(uploaded_file)
            else:
                df_loaded = pd.read_json(uploaded_file)
            
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
                st.success(f"✅ {df_loaded.shape[0]:,} rows × {df_loaded.shape[1]} cols")
        except Exception as e:
            st.error(f"Load error: {e}")

    st.divider()
    st.subheader("🎮 Demo Data")
    demo_cols = st.columns(3)
    demos = {"Iris": px.data.iris, "Tips": px.data.tips, "Gapminder": px.data.gapminder,
             "Wind": px.data.wind, "Stocks": px.data.stocks}
    for i, (name, func) in enumerate(demos.items()):
        if demo_cols[i % 3].button(name, use_container_width=True):
            st.session_state.df = func().copy()
            st.session_state.original_df = st.session_state.df.copy()
            st.session_state.editor_key += 1
            st.rerun()

    if st.button("🗑️ Clear Everything", type="secondary", use_container_width=True):
        for k in ['df', 'original_df', 'last_fig', 'plot_config', 'plot_type']:
            st.session_state[k] = None
        st.session_state.dashboard_plots = []
        st.session_state.editor_key = 0
        st.rerun()

if st.session_state.df is None or st.session_state.df.empty:
    st.info("👈 Upload a file or pick a demo dataset to start.")
    st.stop()

working_df = st.session_state.df.copy()

# ---------- TABS ----------
tab_data, tab_config, tab_viz, tab_dashboard = st.tabs([
    "📋 Data Preview & Edit", "🎨 Plot Configuration", "📈 Visualize & Download", "📊 Dashboard"
])

# ==================== TAB 1: DATA ====================
with tab_data:
    st.subheader("✏️ Interactive Data Editor")
    st.caption("Edit freely → click **Apply Edits** to save.")
    
    edited_df = st.data_editor(
        working_df,
        key=f"editor_{st.session_state.editor_key}",
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True
    )
    
    b1, b2, b3 = st.columns(3)
    if b1.button("💾 Apply Edits", type="primary", use_container_width=True):
        st.session_state.df = edited_df.copy()
        st.session_state.editor_key += 1
        st.success("Saved!")
        st.rerun()
    if b2.button("↩️ Reset to Original", use_container_width=True):
        st.session_state.df = st.session_state.original_df.copy()
        st.session_state.editor_key += 1
        st.rerun()
    if b3.button("🔄 Refresh", use_container_width=True):
        st.rerun()

    with st.expander("🔄 Melt / Select Columns / Group By", expanded=False):
        st.markdown("**Melt (wide → long)**")
        num_cols = [c for c in st.session_state.df.columns if pd.api.types.is_numeric_dtype(st.session_state.df[c])]
        if len(num_cols) >= 2:
            id_vars = st.multiselect("ID columns", [c for c in st.session_state.df.columns if c not in num_cols])
            value_vars = st.multiselect("Value columns", num_cols, default=num_cols[:4])
            if st.button("Melt"):
                melted = pd.melt(st.session_state.df, id_vars=id_vars or None, value_vars=value_vars,
                                 var_name="Metric", value_name="Value")
                st.session_state.df = melted
                st.session_state.editor_key += 1
                st.rerun()

        st.markdown("**Keep only these columns**")
        keep = st.multiselect("Columns to keep", list(st.session_state.df.columns), default=list(st.session_state.df.columns))
        if st.button("Keep selected"):
            st.session_state.df = st.session_state.df[keep]
            st.session_state.editor_key += 1
            st.rerun()

        st.markdown("**Group By & Aggregate**")
        gcols = st.multiselect("Group by", list(st.session_state.df.columns))
        vcols = st.multiselect("Aggregate these", num_cols, default=num_cols[:3])
        agg = st.selectbox("Method", ["mean", "sum", "median", "count", "min", "max"])
        if st.button("Apply Group By") and gcols:
            if agg == "count":
                res = st.session_state.df.groupby(gcols, as_index=False).size().rename(columns={"size": "count"})
            else:
                res = st.session_state.df.groupby(gcols, as_index=False).agg({c: agg for c in vcols})
            st.session_state.df = res
            st.session_state.editor_key += 1
            st.rerun()

# ==================== TAB 2: CONFIG ====================
with tab_config:
    st.subheader("🎨 Configure Your Plot")
    
    all_cols = list(working_df.columns)
    num_cols = [c for c in all_cols if pd.api.types.is_numeric_dtype(working_df[c])]
    cat_cols = [c for c in all_cols if c not in num_cols]
    
    plot_type = st.selectbox("Plot type", [
        "Scatter Plot", "Line Plot", "Bar Chart", "Histogram",
        "Box Plot", "Violin Plot", "Density Heatmap",
        "Pie Chart", "Sunburst Chart", "Treemap", "Scatter Matrix"
    ])
    
    c1, c2 = st.columns(2)
    title = c1.text_input("Title", value=plot_type)
    height = c1.slider("Height", 450, 1200, 680, 25)
    width = c2.slider("Width", 600, 1600, 980, 25)
    template = c2.selectbox("Theme", ["plotly", "plotly_dark", "ggplot2", "seaborn", "simple_white", "presentation"])
    
    # ---------- MAIN VARIABLES ----------
    st.markdown("### 📍 Variables")
    
    needs_x = plot_type in ["Scatter Plot", "Line Plot", "Bar Chart", "Box Plot", "Violin Plot", "Histogram"]
    
    x_col = y_col = None
    multiple_y_cols = None
    use_multiple_y = False
    
    if needs_x:
        x_col = st.selectbox("X variable", all_cols, key="x_var")
        
        if plot_type in ["Scatter Plot", "Line Plot", "Bar Chart", "Box Plot", "Violin Plot", "Histogram"]:
            use_multiple_y = st.checkbox("Use multiple Y variables", value=False)
            
            if use_multiple_y:
                multiple_y_cols = st.multiselect(
                    "Y variables (multiple)",
                    num_cols if num_cols else all_cols,
                    default=num_cols[:min(4, len(num_cols))] if num_cols else [],
                    key="multi_y"
                )
            else:
                y_col = st.selectbox("Y variable", [None] + all_cols, index=1 if len(all_cols) > 1 else 0, key="y_var")
    
    names_col = values_col = path_cols = dimensions = nbins = z_col = None
    
    if plot_type == "Histogram" and not use_multiple_y:
        nbins = st.slider("Number of bins", 5, 80, 20)
    elif plot_type == "Density Heatmap":
        x_col = st.selectbox("X (numeric)", num_cols or all_cols)
        y_col = st.selectbox("Y (numeric)", num_cols or all_cols, index=min(1, len(num_cols)-1) if num_cols else 0)
        z_col = st.selectbox("Intensity (optional)", [None] + num_cols)
    elif plot_type == "Pie Chart":
        names_col = st.selectbox("Labels", cat_cols or all_cols)
        values_col = st.selectbox("Values", num_cols or all_cols)
    elif plot_type in ["Sunburst Chart", "Treemap"]:
        path_cols = st.multiselect("Hierarchy path (order matters)", all_cols, default=all_cols[:3])
        values_col = st.selectbox("Size column", num_cols or all_cols)
    elif plot_type == "Scatter Matrix":
        dimensions = st.multiselect("Variables", num_cols or all_cols, default=(num_cols or all_cols)[:5])
    
    # Appearance
    st.markdown("### 🎨 Appearance")
    color_col = st.selectbox("Color by", [None] + all_cols)
    symbol_col = size_col = None
    if plot_type in ["Scatter Plot", "Scatter Matrix"]:
        symbol_col = st.selectbox("Symbol by", [None] + cat_cols)
        if plot_type == "Scatter Plot":
            size_col = st.selectbox("Size by", [None] + num_cols)
    
    # Faceting
    st.markdown("### 📐 Faceting")
    facet_style = st.radio("Mode", ["None", "Facet Wrap", "Facet Grid"], horizontal=True)
    facet_col = facet_row = facet_wrap_col = None
    facet_col_wrap = 3
    if facet_style == "Facet Wrap":
        facet_wrap_col = st.selectbox("Column to wrap", [None] + all_cols)
        facet_col_wrap = st.slider("Max columns per row", 1, 6, 3)
    elif facet_style == "Facet Grid":
        facet_col = st.selectbox("Horizontal (columns)", [None] + all_cols)
        facet_row = st.selectbox("Vertical (rows)", [None] + all_cols)
    
    # Bar options
    bar_width = 0.7
    show_boundaries = False
    boundary_after = []
    
    if plot_type == "Bar Chart":
        st.markdown("### 📊 Bar Chart Options")
        bar_width = st.slider("Bar width", 0.15, 1.0, 0.70, 0.05)
        show_boundaries = st.checkbox("Add vertical boundaries between categories")
        
        if show_boundaries and x_col:
            unique_cats = working_df[x_col].dropna().unique().tolist()
            unique_cats_str = [str(c) for c in unique_cats]
            boundary_after = st.multiselect(
                "Draw a vertical line AFTER these categories",
                options=unique_cats_str,
                help="Select categories after which you want a separator"
            )
    
    # Advanced
    with st.expander("⚙️ More options"):
        a1, a2 = st.columns(2)
        log_x = a1.checkbox("Log X")
        log_y = a1.checkbox("Log Y")
        show_legend = a1.checkbox("Show legend", value=True)
        legend_pos = a1.selectbox("Legend position", ["right", "bottom", "top", "left"])
        opacity = a2.slider("Opacity", 0.2, 1.0, 0.85, 0.05)
        base_marker_size = a2.slider("Marker size", 3, 18, 7)
        
        trendline = marginal_x = marginal_y = barmode = None
        if plot_type == "Scatter Plot":
            trendline = st.selectbox("Trendline", [None, "ols", "lowess"])
            marginal_x = st.selectbox("Marginal X", [None, "histogram", "violin", "box"])
            marginal_y = st.selectbox("Marginal Y", [None, "histogram", "violin", "box"])
        if plot_type == "Bar Chart":
            barmode = st.selectbox("Bar mode", ["group", "stack", "relative"])
        
        x_label = st.text_input("Custom X label", "")
        y_label = st.text_input("Custom Y label", "")
        color_scale = st.selectbox("Color scale", 
            ["Viridis", "Plasma", "Inferno", "Magma", "Cividis", "Turbo", "RdBu", "Spectral", "Set1", "Set2", "Paired"])
    
    # Save config
    st.session_state.plot_config = {
        "plot_type": plot_type, "title": title, "height": height, "width": width, "template": template,
        "x": x_col, "y": y_col, "multiple_y": multiple_y_cols,
        "color": color_col, "symbol": symbol_col, "size": size_col,
        "facet_col": facet_col, "facet_row": facet_row, "facet_wrap_col": facet_wrap_col, "facet_col_wrap": facet_col_wrap,
        "names": names_col, "values": values_col, "path": path_cols, "dimensions": dimensions,
        "nbins": nbins, "z": z_col,
        "bar_width": bar_width, "show_boundaries": show_boundaries, "boundary_after": boundary_after,
        "barmode": barmode, "trendline": trendline, "marginal_x": marginal_x, "marginal_y": marginal_y,
        "log_x": log_x, "log_y": log_y, "show_legend": show_legend, "legend_pos": legend_pos,
        "opacity": opacity, "marker_size": base_marker_size,
        "x_label": x_label, "y_label": y_label, "color_scale": color_scale
    }

# ==================== TAB 3: VISUALIZE ====================
with tab_viz:
    st.subheader("📈 Preview")
    
    if st.button("🚀 Generate Plot", type="primary", use_container_width=True):
        cfg = st.session_state.plot_config
        ptype = cfg["plot_type"]
        df_plot = st.session_state.df.copy()
        
        try:
            # ========== NEW: Drop empty facets ==========
            facet_vars = []
            if cfg.get("facet_wrap_col"):
                facet_vars.append(cfg["facet_wrap_col"])
            if cfg.get("facet_col"):
                facet_vars.append(cfg["facet_col"])
            if cfg.get("facet_row"):
                facet_vars.append(cfg["facet_row"])
            
            y_cols = []
            if cfg.get("multiple_y"):
                y_cols = [c for c in cfg["multiple_y"] if c in df_plot.columns]
            elif cfg.get("y") and cfg.get("y") in df_plot.columns:
                y_cols = [cfg["y"]]
            
            if facet_vars and y_cols:
                # Keep only rows that have at least one non-null Y
                mask = df_plot[y_cols].notna().any(axis=1)
                df_valid = df_plot.loc[mask]
                
                for fv in facet_vars:
                    if fv in df_valid.columns:
                        valid_levels = df_valid[fv].dropna().unique()
                        df_plot = df_plot[df_plot[fv].isin(valid_levels)].copy()
            # ===========================================
            
            labels = {}
            if cfg.get("x_label"): labels[cfg.get("x")] = cfg["x_label"]
            if cfg.get("y_label"): labels[cfg.get("y")] = cfg["y_label"]
            
            base = dict(title=cfg["title"], height=cfg["height"], width=cfg["width"],
                        template=cfg["template"], labels=labels or None)
            
            facet = {}
            if cfg.get("facet_col"): facet["facet_col"] = cfg["facet_col"]
            if cfg.get("facet_row"): facet["facet_row"] = cfg["facet_row"]
            if cfg.get("facet_wrap_col"):
                facet["facet_col"] = cfg["facet_wrap_col"]
                facet["facet_col_wrap"] = cfg.get("facet_col_wrap", 3)
            
            color_kw = {}
            if cfg.get("color"):
                color_kw["color"] = cfg["color"]
                cscale = cfg.get("color_scale", "Viridis")
                if cfg["color"] in num_cols and ptype in ["Scatter Plot", "Bar Chart", "Histogram", "Box Plot", "Violin Plot"]:
                    color_kw["color_continuous_scale"] = cscale.lower()
                else:
                    color_kw["color_discrete_sequence"] = getattr(px.colors.qualitative, cscale, px.colors.qualitative.Plotly)
            
            y_data = cfg.get("multiple_y") if cfg.get("multiple_y") else cfg.get("y")
            fig = None
            
            if ptype == "Scatter Plot":
                fig = px.scatter(df_plot, x=cfg["x"], y=y_data, symbol=cfg.get("symbol"), size=cfg.get("size"),
                                 trendline=cfg.get("trendline"), marginal_x=cfg.get("marginal_x"),
                                 marginal_y=cfg.get("marginal_y"), **base, **facet, **color_kw)
                if cfg.get("marker_size") and not cfg.get("size"):
                    fig.update_traces(marker_size=cfg["marker_size"])
            
            elif ptype == "Line Plot":
                fig = px.line(df_plot, x=cfg["x"], y=y_data, markers=True, **base, **facet, **color_kw)
            
            elif ptype == "Bar Chart":
                fig = px.bar(df_plot, x=cfg["x"], y=y_data, barmode=cfg.get("barmode", "group"),
                             **base, **facet, **color_kw)
                fig.update_traces(width=cfg.get("bar_width", 0.7))
                
                if cfg.get("show_boundaries") and cfg.get("boundary_after") and cfg.get("x"):
                    cats = df_plot[cfg["x"]].dropna().unique().tolist()
                    cat_to_pos = {str(c): i for i, c in enumerate(cats)}
                    shapes = []
                    for cat_str in cfg["boundary_after"]:
                        if cat_str in cat_to_pos:
                            pos = cat_to_pos[cat_str] + 0.5
                            shapes.append(dict(
                                type="line", x0=pos, x1=pos, y0=0, y1=1, yref="paper",
                                line=dict(color="rgba(60,60,60,0.7)", width=1.8, dash="dot")
                            ))
                    if shapes:
                        fig.update_layout(shapes=shapes)
            
            elif ptype == "Histogram":
                fig = px.histogram(df_plot, x=cfg["x"] if not cfg.get("multiple_y") else None,
                                   y=y_data if cfg.get("multiple_y") else None,
                                   nbins=cfg.get("nbins", 20), **base, **facet, **color_kw)
            
            elif ptype == "Box Plot":
                fig = px.box(df_plot, x=cfg["x"], y=y_data, points="outliers", **base, **facet, **color_kw)
            
            elif ptype == "Violin Plot":
                fig = px.violin(df_plot, x=cfg["x"], y=y_data, box=True, points="outliers", **base, **facet, **color_kw)
            
            elif ptype == "Density Heatmap":
                fig = px.density_heatmap(df_plot, x=cfg["x"], y=cfg["y"], z=cfg.get("z"),
                                         color_continuous_scale=cfg.get("color_scale", "Viridis").lower(), **base, **facet)
            
            elif ptype == "Pie Chart":
                fig = px.pie(df_plot, names=cfg["names"], values=cfg["values"], hole=0.35,
                             title=cfg["title"], height=cfg["height"], width=cfg["width"], template=cfg["template"])
            
            elif ptype == "Sunburst Chart":
                fig = px.sunburst(df_plot, path=cfg.get("path", []), values=cfg.get("values"),
                                  color=cfg.get("color"), title=cfg["title"],
                                  height=cfg["height"], width=cfg["width"], template=cfg["template"])
            
            elif ptype == "Treemap":
                fig = px.treemap(df_plot, path=cfg.get("path", []), values=cfg.get("values"),
                                 color=cfg.get("color"), title=cfg["title"],
                                 height=cfg["height"], width=cfg["width"], template=cfg["template"])
            
            elif ptype == "Scatter Matrix":
                fig = px.scatter_matrix(df_plot, dimensions=cfg.get("dimensions", []),
                                        color=cfg.get("color"), title=cfg["title"],
                                        height=cfg["height"], width=cfg["width"], template=cfg["template"])
            
            if fig:
                orient = "h" if cfg.get("legend_pos") in ["bottom", "top"] else "v"
                fig.update_layout(showlegend=cfg.get("show_legend", True),
                                  legend=dict(orientation=orient, y=1.02 if orient=="h" else 0.5,
                                              x=0.5 if orient=="h" else 1.02))
                if cfg.get("log_x"): fig.update_xaxes(type="log")
                if cfg.get("log_y"): fig.update_yaxes(type="log")
                if cfg.get("opacity") and ptype in ["Scatter Plot", "Line Plot", "Bar Chart"]:
                    fig.update_traces(marker_opacity=cfg["opacity"])
                
                st.session_state.last_fig = fig
                st.success("✅ Ready — empty facets were automatically removed")
        
        except Exception as e:
            st.error(str(e))
            st.exception(e)
    
    if st.session_state.last_fig is not None:
        st.plotly_chart(st.session_state.last_fig, use_container_width=True)
        
        if st.button("➕ Add this plot to Dashboard"):
            cfg = st.session_state.plot_config.copy()
            cfg["id"] = len(st.session_state.dashboard_plots) + 1
            st.session_state.dashboard_plots.append(cfg)
            st.success(f"Added (total: {len(st.session_state.dashboard_plots)})")
            st.rerun()
        
        st.divider()
        d1, d2, d3 = st.columns(3)
        with d1:
            try:
                buf = BytesIO()
                st.session_state.last_fig.write_html(buf, include_plotlyjs="cdn", full_html=True)
                st.download_button("🌐 HTML", buf.getvalue(), f"plot_{datetime.now():%Y%m%d_%H%M%S}.html", "text/html")
            except: pass
        with d2:
            try:
                buf = BytesIO()
                st.session_state.last_fig.write_image(buf, format="png", scale=2)
                st.download_button("🖼️ PNG", buf.getvalue(), f"plot_{datetime.now():%Y%m%d_%H%M%S}.png", "image/png")
            except:
                st.caption("PNG needs kaleido")
        with d3:
            buf = BytesIO()
            st.session_state.df.to_csv(buf, index=False)
            st.download_button("📄 CSV", buf.getvalue(), f"data_{datetime.now():%Y%m%d_%H%M%S}.csv", "text/csv")

# ==================== TAB 4: DASHBOARD ====================
with tab_dashboard:
    st.subheader("📊 Dashboard")
    
    if not st.session_state.dashboard_plots:
        st.info("Add plots from the Visualize tab")
    else:
        layout = st.selectbox("Columns", [1, 2, 3], index=1)
        if st.button("🗑️ Clear dashboard"):
            st.session_state.dashboard_plots = []
            st.rerun()
        
        cols = st.columns(layout)
        figs_for_download = []
        
        for i, cfg in enumerate(st.session_state.dashboard_plots):
            with cols[i % layout]:
                st.markdown(f"**{cfg.get('title', f'Plot {i+1}')}**")
                try:
                    df = st.session_state.df.copy()
                    
                    # Also drop empty facets in dashboard
                    facet_vars = [v for v in [cfg.get("facet_wrap_col"), cfg.get("facet_col"), cfg.get("facet_row")] if v]
                    y_cols = cfg.get("multiple_y") or ([cfg.get("y")] if cfg.get("y") else [])
                    y_cols = [c for c in y_cols if c in df.columns]
                    if facet_vars and y_cols:
                        mask = df[y_cols].notna().any(axis=1)
                        valid = df.loc[mask]
                        for fv in facet_vars:
                            if fv in valid.columns:
                                df = df[df[fv].isin(valid[fv].unique())]
                    
                    y_val = cfg.get("multiple_y") or cfg.get("y")
                    ptype = cfg["plot_type"]
                    fig = None
                    
                    if ptype == "Bar Chart":
                        fig = px.bar(df, x=cfg.get("x"), y=y_val, color=cfg.get("color"),
                                     barmode=cfg.get("barmode", "group"), title=cfg.get("title"), height=380)
                        fig.update_traces(width=cfg.get("bar_width", 0.7))
                        if cfg.get("show_boundaries") and cfg.get("boundary_after") and cfg.get("x"):
                            cats = df[cfg["x"]].dropna().unique().tolist()
                            cat_to_pos = {str(c): i for i, c in enumerate(cats)}
                            shapes = []
                            for cat in cfg["boundary_after"]:
                                if cat in cat_to_pos:
                                    pos = cat_to_pos[cat] + 0.5
                                    shapes.append(dict(type="line", x0=pos, x1=pos, y0=0, y1=1, yref="paper",
                                                       line=dict(color="rgba(60,60,60,0.7)", width=1.6, dash="dot")))
                            if shapes:
                                fig.update_layout(shapes=shapes)
                    elif ptype == "Line Plot":
                        fig = px.line(df, x=cfg.get("x"), y=y_val, color=cfg.get("color"), markers=True,
                                      title=cfg.get("title"), height=380)
                    elif ptype == "Scatter Plot":
                        fig = px.scatter(df, x=cfg.get("x"), y=y_val, color=cfg.get("color"),
                                         title=cfg.get("title"), height=380)
                    elif ptype == "Box Plot":
                        fig = px.box(df, x=cfg.get("x"), y=y_val, color=cfg.get("color"), points="outliers",
                                     title=cfg.get("title"), height=380)
                    elif ptype == "Violin Plot":
                        fig = px.violin(df, x=cfg.get("x"), y=y_val, color=cfg.get("color"), box=True,
                                        title=cfg.get("title"), height=380)
                    elif ptype == "Histogram":
                        fig = px.histogram(df, x=cfg.get("x"), color=cfg.get("color"),
                                           nbins=cfg.get("nbins", 20), title=cfg.get("title"), height=380)
                    elif ptype == "Pie Chart":
                        fig = px.pie(df, names=cfg.get("names"), values=cfg.get("values"),
                                     title=cfg.get("title"), height=380)
                    
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, key=f"d{i}")
                        figs_for_download.append(fig)
                    
                    if st.button("❌", key=f"rm{i}"):
                        st.session_state.dashboard_plots.pop(i)
                        st.rerun()
                except Exception as e:
                    st.error(str(e))
        
        st.divider()
        if figs_for_download:
            try:
                html = "<html><body><h1>Dashboard</h1>"
                for i, f in enumerate(figs_for_download):
                    html += f"<h3>Plot {i+1}</h3>" + f.to_html(full_html=False, include_plotlyjs='cdn' if i==0 else False)
                html += "</body></html>"
                st.download_button("🌐 Download Dashboard (HTML)", html,
                                   f"dashboard_{datetime.now():%Y%m%d_%H%M%S}.html", "text/html")
            except: pass

st.caption("DataViz Studio – Empty facets are automatically hidden")
