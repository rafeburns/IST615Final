"""
Streamlit frontend for the CSV Processing Pipeline.
Upload CSVs, view cleaned data and summary stats.
"""

import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
from azure.storage.blob import BlobServiceClient

st.set_page_config(page_title="CSV Processing Pipeline", layout="wide")
st.title("CSV Processing Pipeline")
st.caption("Upload a CSV file → auto-cleaned and analyzed via Azure Functions")

# --- Sidebar: Azure connection ---
with st.sidebar:
    st.header("Azure Connection")
    conn_str = st.text_input("Storage Connection String", type="password",
                             help="From Azure Portal → Storage Account → Access Keys")
    upload_container = st.text_input("Upload Container", value="uploads")
    output_container = st.text_input("Output Container", value="output")

if not conn_str:
    st.info("Enter your Azure Storage connection string in the sidebar to get started.")
    st.stop()

# Connect to Azure Blob Storage
try:
    blob_service = BlobServiceClient.from_connection_string(conn_str)
except Exception as e:
    st.error(f"Connection failed: {e}")
    st.stop()


# --- Tab layout ---
tab_upload, tab_results = st.tabs(["Upload", "Results"])


# ── Upload Tab ──
with tab_upload:
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

    if uploaded_file:
        # Preview the raw data
        st.subheader("Preview (raw)")
        df_preview = pd.read_csv(io.BytesIO(uploaded_file.getvalue()))
        st.dataframe(df_preview, use_container_width=True)

        if st.button("Upload to Pipeline", type="primary"):
            try:
                container_client = blob_service.get_container_client(upload_container)
                # Ensure container exists
                try:
                    container_client.create_container()
                except Exception:
                    pass

                blob_name = f"{uploaded_file.name}"
                container_client.upload_blob(blob_name, uploaded_file.getvalue(), overwrite=True)
                st.success(f"Uploaded **{blob_name}** — Azure Function will process it automatically.")
                st.info("Switch to the **Results** tab in a few seconds to see output.")
            except Exception as e:
                st.error(f"Upload failed: {e}")


# ── Results Tab ──
with tab_results:
    try:
        out_client = blob_service.get_container_client(output_container)
        blobs = list(out_client.list_blobs())
    except Exception:
        st.warning("Output container not found yet. Upload a file first.")
        st.stop()

    if not blobs:
        st.info("No processed results yet. Upload a CSV first.")
    else:
        # Group by summaries and cleaned files
        summaries = sorted([b for b in blobs if b.name.startswith("summaries/")],
                           key=lambda b: b.last_modified, reverse=True)
        cleaned = sorted([b for b in blobs if b.name.startswith("cleaned/")],
                         key=lambda b: b.last_modified, reverse=True)

        if summaries:
            st.subheader("Latest Summary")
            latest = summaries[0]
            data = out_client.download_blob(latest.name).readall().decode("utf-8")
            summary = json.loads(data)

            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Original Rows", summary["original_row_count"])
            col2.metric("Cleaned Rows", summary["cleaned_row_count"])
            col3.metric("Dropped (Empty)", summary["rows_dropped_empty"])
            col4.metric("Duplicates Removed", summary["duplicates_removed"])

            # Numeric stats
            if summary.get("numeric_column_stats"):
                st.subheader("Numeric Column Stats")
                stats_df = pd.DataFrame(summary["numeric_column_stats"]).T
                st.dataframe(stats_df, use_container_width=True)

            with st.expander("Full summary JSON"):
                st.json(summary)

        if cleaned:
            st.subheader("Cleaned Data")
            latest_clean = cleaned[0]
            csv_data = out_client.download_blob(latest_clean.name).readall().decode("utf-8")
            df_clean = pd.read_csv(io.StringIO(csv_data))
            st.dataframe(df_clean, use_container_width=True)

            st.download_button("Download Cleaned CSV", csv_data,
                               file_name=latest_clean.name.split("/")[-1],
                               mime="text/csv")

        # History
        if len(summaries) > 1:
            st.subheader("Processing History")
            for s in summaries:
                st.text(f"  {s.name}  ({s.last_modified.strftime('%Y-%m-%d %H:%M')})")
