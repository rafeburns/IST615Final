"""
CSV Processing Pipeline — Upload, clean, and analyze CSV files.
"""

import streamlit as st
import pandas as pd
import io
import csv
import json

st.set_page_config(page_title="DataPipe", layout="wide", initial_sidebar_state="collapsed")


# ──────────────────────────────────────────────
#  Processing logic
# ──────────────────────────────────────────────

def run_pipeline(raw_csv):
    reader = csv.DictReader(io.StringIO(raw_csv))
    headers = reader.fieldnames
    if not headers:
        raise ValueError("CSV file has no headers")

    rows = list(reader)
    total_rows = len(rows)

    cleaned = []
    dropped = 0
    duplicates_removed = 0
    seen = set()

    for row in rows:
        row = {k: v.strip() if v else "" for k, v in row.items()}

        if all(v == "" for v in row.values()):
            dropped += 1
            continue

        key = tuple(row.values())
        if key in seen:
            duplicates_removed += 1
            continue
        seen.add(key)

        for col in row:
            if row[col] == "":
                row[col] = _fill_default(col, rows)

        cleaned.append(row)

    numeric_cols = _detect_numeric_columns(cleaned, headers)
    stats = {}
    for col in numeric_cols:
        values = []
        for r in cleaned:
            try:
                values.append(float(r[col]))
            except (ValueError, TypeError):
                continue
        if values:
            stats[col] = {
                "count": len(values),
                "mean": round(sum(values) / len(values), 2),
                "min": min(values),
                "max": max(values),
                "sum": round(sum(values), 2),
            }

    summary = {
        "original_row_count": total_rows,
        "cleaned_row_count": len(cleaned),
        "rows_dropped_empty": dropped,
        "duplicates_removed": duplicates_removed,
        "columns": headers,
        "numeric_column_stats": stats,
    }

    return cleaned, summary


def _detect_numeric_columns(rows, headers):
    numeric = []
    for col in headers:
        num_count = 0
        total = 0
        for r in rows:
            val = r.get(col, "")
            if val in ("", "N/A"):
                continue
            total += 1
            try:
                float(val)
                num_count += 1
            except ValueError:
                pass
        if total > 0 and (num_count / total) > 0.5:
            numeric.append(col)
    return numeric


def _fill_default(column_name, all_rows):
    num_count = 0
    total = 0
    for r in all_rows:
        val = r.get(column_name, "").strip()
        if val == "":
            continue
        total += 1
        try:
            float(val)
            num_count += 1
        except ValueError:
            pass
    if total > 0 and (num_count / total) > 0.5:
        return "0"
    return "N/A"


# ── Custom CSS to hide Streamlit branding and style like a modern app ──
st.markdown("""
<style>
    /* Hide Streamlit extras */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stToolbar"] {display: none;}
    [data-testid="stDecoration"] {display: none;}

    /* Dark modern theme */
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    }

    /* Top nav bar */
    .navbar {
        background: rgba(255,255,255,0.03);
        backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(255,255,255,0.06);
        padding: 16px 32px;
        margin: -80px -80px 32px -80px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .navbar-brand {
        font-size: 22px;
        font-weight: 700;
        color: #e0e0e0;
        letter-spacing: -0.5px;
    }
    .navbar-dot {
        width: 8px; height: 8px;
        background: #6c5ce7;
        border-radius: 50%;
        display: inline-block;
    }
    .navbar-sub {
        font-size: 13px;
        color: #888;
        margin-left: auto;
    }

    /* Cards */
    .card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        transition: border-color 0.2s;
    }
    .card:hover {
        border-color: rgba(108, 92, 231, 0.3);
    }
    .card-title {
        font-size: 13px;
        font-weight: 600;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 16px;
    }

    /* Stat cards */
    .stat-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 24px;
    }
    .stat-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .stat-value {
        font-size: 32px;
        font-weight: 700;
        color: #e0e0e0;
    }
    .stat-label {
        font-size: 12px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }
    .stat-card:nth-child(1) .stat-value { color: #a29bfe; }
    .stat-card:nth-child(2) .stat-value { color: #55efc4; }
    .stat-card:nth-child(3) .stat-value { color: #fdcb6e; }
    .stat-card:nth-child(4) .stat-value { color: #fd79a8; }

    /* Section headers */
    .section-header {
        font-size: 18px;
        font-weight: 600;
        color: #e0e0e0;
        margin: 32px 0 16px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .section-line {
        flex: 1;
        height: 1px;
        background: rgba(255,255,255,0.08);
    }

    /* Upload zone */
    .upload-zone {
        background: rgba(108, 92, 231, 0.05);
        border: 2px dashed rgba(108, 92, 231, 0.3);
        border-radius: 16px;
        padding: 48px;
        text-align: center;
        margin: 24px 0;
    }
    .upload-icon {
        font-size: 48px;
        margin-bottom: 12px;
    }
    .upload-text {
        font-size: 16px;
        color: #aaa;
    }

    /* Badge */
    .badge {
        display: inline-block;
        background: rgba(108, 92, 231, 0.15);
        color: #a29bfe;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }

    /* Override Streamlit dataframe styling */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        overflow: hidden;
    }

    /* Button overrides */
    .stButton > button {
        background: linear-gradient(135deg, #6c5ce7, #a29bfe);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(108, 92, 231, 0.4);
    }

    /* Download button */
    .stDownloadButton > button {
        background: rgba(255,255,255,0.06);
        color: #e0e0e0;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px;
    }

    /* File uploader styling */
    [data-testid="stFileUploader"] {
        background: rgba(108, 92, 231, 0.05);
        border: 2px dashed rgba(108, 92, 231, 0.25);
        border-radius: 16px;
        padding: 20px;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: rgba(255,255,255,0.03);
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #888;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(108, 92, 231, 0.2);
        color: #a29bfe;
    }

    /* JSON expander */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.03);
        border-radius: 8px;
    }

    @media (max-width: 768px) {
        .stat-grid { grid-template-columns: repeat(2, 1fr); }
    }
</style>
""", unsafe_allow_html=True)

# ── Navbar ──
st.markdown("""
<div class="navbar">
    <span class="navbar-dot"></span>
    <span class="navbar-brand">DataPipe</span>
    <span class="badge">v1.0</span>
    <span class="navbar-sub">CSV Processing Pipeline</span>
</div>
""", unsafe_allow_html=True)

# ── Upload Section ──
st.markdown('<div class="card"><div class="card-title">Upload</div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Drop your CSV file here", type=["csv"], label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

if not uploaded_file:
    st.markdown("""
    <div style="text-align:center; padding: 60px 20px; color: #666;">
        <div style="font-size: 40px; margin-bottom: 16px;">&#8593;</div>
        <div style="font-size: 16px;">Upload a CSV file to get started</div>
        <div style="font-size: 13px; color: #555; margin-top: 8px;">
            Supports any CSV with headers. Files are processed locally.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Read raw CSV
raw_csv = uploaded_file.getvalue().decode("utf-8")
df_raw = pd.read_csv(io.StringIO(raw_csv))

# ── Tabs: Raw Data / Results ──
tab_raw, tab_results = st.tabs(["Raw Data", "Results"])

with tab_raw:
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <span style="color:#888; font-size:13px;">{len(df_raw)} rows x {len(df_raw.columns)} columns</span>
        <span class="badge">{uploaded_file.name}</span>
    </div>
    """, unsafe_allow_html=True)
    st.dataframe(df_raw, use_container_width=True, height=400)

with tab_results:
    col_btn, col_space = st.columns([1, 3])
    with col_btn:
        process = st.button("Run Pipeline", type="primary")

    if process:
        with st.spinner("Processing..."):
            cleaned_rows, summary = run_pipeline(raw_csv)
            st.session_state["cleaned"] = cleaned_rows
            st.session_state["summary"] = summary

    if "summary" not in st.session_state:
        st.markdown("""
        <div style="text-align:center; padding: 60px; color: #666;">
            <div style="font-size: 16px;">Click <strong>Run Pipeline</strong> to process your data</div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    summary = st.session_state["summary"]
    cleaned_rows = st.session_state["cleaned"]

    # ── Stat Cards ──
    st.markdown(f"""
    <div class="stat-grid">
        <div class="stat-card">
            <div class="stat-value">{summary["original_row_count"]}</div>
            <div class="stat-label">Original Rows</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{summary["cleaned_row_count"]}</div>
            <div class="stat-label">Cleaned Rows</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{summary["rows_dropped_empty"]}</div>
            <div class="stat-label">Dropped Empty</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{summary["duplicates_removed"]}</div>
            <div class="stat-label">Duplicates Removed</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Numeric Stats ──
    if summary.get("numeric_column_stats"):
        st.markdown("""
        <div class="section-header">
            Numeric Stats <div class="section-line"></div>
        </div>
        """, unsafe_allow_html=True)
        stats_df = pd.DataFrame(summary["numeric_column_stats"]).T
        st.dataframe(stats_df, use_container_width=True)

    # ── Cleaned Data ──
    if cleaned_rows:
        st.markdown("""
        <div class="section-header">
            Cleaned Data <div class="section-line"></div>
        </div>
        """, unsafe_allow_html=True)

        df_clean = pd.DataFrame(cleaned_rows)

        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <span style="color:#888; font-size:13px;">{len(df_clean)} rows x {len(df_clean.columns)} columns</span>
            <span class="badge">cleaned</span>
        </div>
        """, unsafe_allow_html=True)

        st.dataframe(df_clean, use_container_width=True, height=400)

        st.download_button(
            "Download Cleaned CSV",
            df_clean.to_csv(index=False),
            file_name=f"cleaned_{uploaded_file.name}",
            mime="text/csv",
        )

    # ── JSON Summary ──
    with st.expander("View Full Summary JSON"):
        st.json(summary)
