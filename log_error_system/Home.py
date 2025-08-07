# app.py
import streamlit as st
import os
import re
import pandas as pd
import zipfile
import tempfile
import json
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from database.solutions_writer import write_solution
from parser.log_parser import parse_log_line, is_error_log, is_warning_log
from database.solutions_db import find_solution, save_ai_prediction, ai_predicted_cache
from ai_model.model import predict_solution           
from api_fallback.fallback_api import fetch_solution_from_api
from ai_model.category_fixes import CATEGORY_TO_FIX
from api_fallback.fetch_solution_from_ollama import fetch_solution_from_ollama

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

# Simulated upload class
class SimulatedUploadFile:
    def __init__(self, name, content):
        self.name = name
        self._content = content

    def read(self):
        return self._content

st.markdown("""
<style>
.nav-bar {
    display: flex;
    justify-content: flex-end;
    background-color: #2C2F38;  /* Dark grey bar */
    padding: 8px 20px;
    border-radius: 0;
    font-family: Arial, sans-serif;
}

.nav-bar a {
    color: white;
    margin-left: 25px;
    text-decoration: none;
    font-weight: 500;
    font-size: 14px;
}

.nav-bar a:hover {
    text-decoration: underline;
}
</style>

<div class="nav-bar">
    <a href="?nav=main">Main</a>
    <a href="?nav=editdb">Edit DB</a>
</div>
""", unsafe_allow_html=True)

# Page setup
st.set_page_config(page_title="Log Analyzer", layout="wide")
# Navigation control
nav = st.query_params.get("nav", "main")

if nav == "editdb":
    from database.solution_editor import render_solution_editor
    st.set_page_config(page_title="Edit DB", layout="wide")
    st.title("🛠️ Solution Database Editor")
    render_solution_editor()
    st.stop()  # Stops rest of code from running
else:
    st.set_page_config(page_title="Log Analyzer", layout="wide")
    st.title("📊 Bank e-Agent Log Error Analyzer")

st.markdown("Automatically scans `.log` and `.txt` files inside the `logs/` folder.")

# Session state fix
if "file_content_map" not in st.session_state:
    st.session_state["file_content_map"] = {}

if "all_entries" not in st.session_state:
    st.session_state["all_entries"] = []

if "log_processing_done" not in st.session_state:
    st.session_state["log_processing_done"] = False

# Upload logs manually instead of auto-loading from folder

uploaded_files = st.file_uploader(
    "📤 Upload log files or a ZIP file", 
    type=["log", "txt", "zip"], 
    accept_multiple_files=True
)

all_files = []

if uploaded_files:
    for uploaded in uploaded_files:
        # Handle zip files
        if uploaded.name.endswith(".zip"):
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, uploaded.name)

                with open(zip_path, "wb") as f:
                    f.write(uploaded.getbuffer())

                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(tmpdir)

                for root, _, files in os.walk(tmpdir):
                    for filename in files:
                        if filename.endswith((".log", ".txt")):
                            filepath = os.path.join(root, filename)
                            with open(filepath, "rb") as f:
                                content = f.read()
                                all_files.append(SimulatedUploadFile(filename, content))
        # Handle individual log/txt files
        elif uploaded.name.endswith((".log", ".txt")):
            content = uploaded.read()
            all_files.append(SimulatedUploadFile(uploaded.name, content))
else:
    st.warning("⚠️ Please upload one or more `.log`, `.txt`, or `.zip` files.")
    st.stop()


# File selection
st.subheader("📁 Select Log Files")
def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

available_filenames = sorted([file.name for file in all_files], key=natural_sort_key)

if "file_selector" not in st.session_state:
    st.session_state.file_selector = available_filenames[:1]

# Button logic BEFORE widget rendering
col1, col2, col3 = st.columns([3, 1, 1])
with col2:
    if st.button("📂 Select All"):
        st.session_state.file_selector = available_filenames
        st.rerun()

with col3:
    if st.button("❌ Deselect All"):
        st.session_state.file_selector = []
        st.rerun()

# Now render the widget
with col1:
    selected_filenames = st.multiselect("Choose file(s)", available_filenames, default=st.session_state.file_selector, key="file_selector")

# Raw Log Viewer
st.markdown("### 📜 Raw Log Viewer")
with st.expander("Click to view raw log file content", expanded=False):
    selected_raw_file = st.selectbox("Choose log file", available_filenames)
    search_keyword = st.text_input("🔍 Search in raw log")
    strict_match = st.checkbox("🔒 Strict match (full line only)", value=False)
    lines_per_page = st.number_input("Lines per page", min_value=10, max_value=1000, value=100, step=10)

    for file in all_files:
        if file.name == selected_raw_file:
            try:
                raw_text = file.read().decode("utf-8")
            except UnicodeDecodeError:
                raw_text = file.read().decode("latin-1")

            def highlight_log_levels(text):
                text = re.sub(r"\[ERROR\s*\]", r"<span style='color: red; font-weight:bold;'>[ERROR]</span>", text)
                text = re.sub(r"\[WARN\s*\]", r"<span style='color: orange; font-weight:bold;'>[WARN]</span>", text)
                text = re.sub(r"\[INFO\s*\]", r"<span style='color: limegreen; font-weight:bold;'>[INFO]</span>", text)
                text = re.sub(r"\[DEBUG\s*\]", r"<span style='color: violet; font-weight:bold;'>[DEBUG]</span>", text)
                return text

            lines = raw_text.splitlines()
            total_lines = len(lines)
            extracted_lines = []

            if search_keyword:
                norm_search = " ".join(search_keyword.strip().lower().split())
                matching = [i for i, line in enumerate(lines) if (norm_search == line.strip().lower() if strict_match else norm_search in line.lower())]
                for idx in matching:
                    extracted_lines.extend(lines[max(0, idx - 5): min(total_lines, idx + 6)])
            else:
                total_pages = max(1, (total_lines - 1) // lines_per_page + 1)
                current_page = st.number_input("Page", 1, total_pages, 1)
                start, end = (current_page - 1) * lines_per_page, min(current_page * lines_per_page, total_lines)
                extracted_lines = lines[start:end]

            slider_range = st.slider("Line range", 0, total_lines - 1, (0, min(100, total_lines - 1))) if total_lines else (0, 0)
            slider_lines = lines[slider_range[0]:slider_range[1] + 1] if total_lines else []
            combined_lines = sorted(set(extracted_lines + slider_lines), key=lambda x: lines.index(x))
            highlighted = highlight_log_levels("\n".join(combined_lines))

            st.markdown(f"""
                <div style="background-color:#0e1117;padding:1em;border-radius:10px;height:400px;overflow-y:auto;white-space:pre-wrap;font-family:Courier New;font-size:14px;color:white;">
                {highlighted}</div>
            """, unsafe_allow_html=True)
            break

CATEGORY_TO_FIX = {
    "network": "Check VPN, firewall, and DNS settings.",
    "database": "Check DB credentials and host reachability.",
    "timeout": "Increase timeout or investigate server delay.",
    "authentication": "Verify user credentials and session configs.",
    "file": "Ensure the file exists and has proper permissions."
}

# Solution caching
@lru_cache(maxsize=None)
def get_solution_cached(message: str) -> str:
    # 1️⃣ Check database
    db_solution = find_solution(message)
    if db_solution and db_solution != "No solution found.":
        return f"🗂 DB Solution: {db_solution}"

    # 2️⃣ Check AI prediction cache
    if message in ai_predicted_cache:
        category = ai_predicted_cache[message]
        confidence = None
    else:
        try:
            category = predict_solution(message,return_confidence=True)
            save_ai_prediction(message, category)
        except Exception as e:
            print("❌ AI Prediction failed:", e)
            category = None
            confidence = None

    # 3️⃣ Category → fix mapping
    if category and category in CATEGORY_TO_FIX:
        fix = CATEGORY_TO_FIX[category]
        conf_text = f" (Confidnce: {confidence:.0%})" if confidence is not None else ""
        return f"🤖 AI Predicted: **{category}**\n💡 Suggested Fix: {fix}"

    # 4️⃣ Optional API fallback
    try:
     api_sol = fetch_solution_from_api(message)
     if api_sol and "API Error" not in api_sol:
        write_solution(message, api_sol)
        return f"🌐 API Fallback: (Saved){api_sol}"
     return f"🌐 API Fallback: {api_sol}"
    except Exception as e:
      return f"❌ No fix found. ({e})"


     # 4️⃣ Ollama offline fallback
   # try:
   #     ollama_sol = fetch_solution_from_ollama(message)
   #     return f"🖥️ Ollama Fallback: {ollama_sol}"
   # except Exception as e:
   #     return f"❌ No fix found. ({e})"


# Timestamp parsing
def parse_timestamp(ts_str):
    ts_str = ts_str.strip()
    for fmt in ["%Y-%m-%d %H:%M:%S,%f", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y/%m/%d %H:%M:%S"]:
        try: return datetime.strptime(ts_str, fmt)
        except: continue
    return datetime.min

# Process and display logs
if selected_filenames:
    selected_files = [f for f in all_files if f.name in selected_filenames]

    if st.button("🚀 Start Log Processing"):
        st.session_state["log_processing_done"] = False
        temp_map = {}

        def process_file(file):
            entries = []
            if file.name not in temp_map:
             content = file.read().decode("utf-8", errors="ignore")
             temp_map[file.name] = content
            else:
             content = temp_map[file.name]

            temp_map[file.name] = content
            for line in content.splitlines():
             parsed = parse_log_line(line)
             if parsed:
               solution = ""
               if parsed["level"] in ["ERROR", "WARN", "DEBUG"]:
                  solution = get_solution_cached(parsed["message"])
               entries.append({
                 "filename": file.name,
                 "timestamp": parsed["timestamp"],
                 "level": parsed["level"],
                 "message": parsed["message"],
                 "solution": solution
       })

            return entries

        with st.spinner("Processing logs..."):
            all_entries = []
            with ThreadPoolExecutor() as executor:
                for result in executor.map(process_file, selected_files):
                    all_entries.extend(result)

        st.session_state["file_content_map"] = temp_map
        st.session_state["all_entries"] = all_entries
        st.session_state["log_processing_done"] = True

    if st.session_state["log_processing_done"]:
        entries = st.session_state["all_entries"]
        entries.sort(key=lambda x: parse_timestamp(x['timestamp']))
        grouped = defaultdict(list)
        for e in entries:
            grouped[e['filename']].append(e)

        st.subheader("🔍 Filter Options")
        log_files = sorted(grouped.keys(), key=natural_sort_key)
        if "log_selector" not in st.session_state:
         st.session_state.log_selector = log_files[:1]

        fcol1, fcol2, fcol3 = st.columns([3, 1, 1])
        with fcol2:
         if st.button("✅ All Logs"):
          st.session_state.log_selector = log_files
          st.rerun()
        with fcol3:
         if st.button("❌ Clear Logs"):
          st.session_state.log_selector = []
          st.rerun()

        with fcol1:
    # Ensure default selections are valid (prevent crash)
         if "log_selector" in st.session_state:
           valid_defaults = [f for f in st.session_state.log_selector if f in log_files]
         else:
           valid_defaults = log_files[:1]  # fallback default

        selected_logs = st.multiselect(
          "Filter by log file(s)",
           log_files,
           default=valid_defaults,
            key="log_selector"
        )

        selected_levels = [lvl for lvl in ["ERROR", "WARN", "DEBUG", "INFO"] if st.checkbox(lvl)]

        with st.expander("📅 Set Date & Time Range", expanded=False):
          start_time = datetime.combine(st.date_input("Start Date", datetime(2025, 1, 1)), st.time_input("Start Time", datetime.strptime("00:00:00", "%H:%M:%S").time()))
          end_time = datetime.combine(st.date_input("End Date", datetime(2030, 1, 1)), st.time_input("End Time", datetime.strptime("23:59:59", "%H:%M:%S").time()))
         
        search_term = st.text_input("Search keyword")

        filtered_data = [e for f in selected_logs for e in grouped[f] if (
            e["level"] in selected_levels and start_time <= parse_timestamp(e["timestamp"]) <= end_time and
            (search_term.lower() in e["message"].lower() or search_term.lower() in e["solution"].lower())
        )]

        if filtered_data:
            df = pd.DataFrame(filtered_data).reset_index(drop=True)
            st.markdown("### 📊 Filtered Log Entries Table")
            st.dataframe(df, use_container_width=True)

            st.markdown("### 📋 View 5 Log Entries Before and After")
            context_range = st.number_input("How many log entries before and after?", min_value=1, max_value=50, value=5, step=1)

            sel_idx = st.number_input("Row index (0–{})".format(len(df) - 1), 0, len(df) - 1, 0)
            sel_entry = df.iloc[sel_idx]
            search_key = sel_entry["message"].strip().lower()
            raw_text = st.session_state["file_content_map"].get(sel_entry["filename"], "")
            raw_lines = raw_text.splitlines()

            log_entry_pattern = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
            log_entries = []
            current_entry = []

            for line in raw_lines:
             if log_entry_pattern.match(line):
              if current_entry:
                log_entries.append("\n".join(current_entry))
              current_entry = [line]
            else:
             current_entry.append(line)
            if current_entry:
             log_entries.append("\n".join(current_entry))

            # Step 2: Search for the message
            matched_idx = next((i for i, entry in enumerate(log_entries) if search_key in entry.lower()), -1)

            if matched_idx != -1:
             start = max(0, matched_idx - context_range)
             end = min(len(log_entries), matched_idx +  context_range + 1)
             context_entries = log_entries[start:end]

            def highlight_levels(text):
               text = re.sub(r"\[ERROR\s*\]", "<span style='color:red;font-weight:bold;'>[ERROR]</span>", text)
               text = re.sub(r"\[WARN\s*\]", "<span style='color:orange;font-weight:bold;'>[WARN]</span>", text)
               text = re.sub(r"\[INFO\s*\]", "<span style='color:limegreen;font-weight:bold;'>[INFO]</span>", text)
               text = re.sub(r"\[DEBUG\s*\]", "<span style='color:violet;font-weight:bold;'>[DEBUG]</span>", text)
               return text

            html_blocks = []
            for i, entry in enumerate(context_entries):
                is_selected = (i + start == matched_idx)
                is_error    = "[ERROR" in entry.upper()
             
                style = "padding:5px;margin-bottom:10px;"
 
                if is_error:
                   style += "background:#331414;"  

                if is_selected:
                   style += "border-left:4px solid yellow;"

                html_blocks.append(f"<div style='{style}'>{highlight_levels(entry)}</div>")

            st.markdown("#### 📜 Raw Context Log")
            st.markdown(
             "<div style='background:#0e1117;padding:10px;border-radius:8px;font-family:"
             "Courier New;font-size:14px;color:white;overflow-x:auto;'>"
            + "\n".join(html_blocks)
            + "</div>",
            unsafe_allow_html=True,
            )
        else:
            st.warning("⚠️ Could not find that log message inside the raw file.")

    else:
        st.warning("⚠️ Please process the logs first.")

    if st.session_state["log_processing_done"] and st.button("🔄 Reset Analysis"):
        st.session_state["log_processing_done"] = False
        st.session_state["all_entries"] = []


