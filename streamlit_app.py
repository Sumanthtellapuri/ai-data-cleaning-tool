import streamlit as st
import requests
import time
import pandas as pd

API="https://ai-data-cleaning-tool.onrender.com"

st.set_page_config(page_title="AI Data Cleaning Tool", layout="wide")

# ---------- DESIGN SYSTEM ----------
st.markdown("""
<style>

/* GLOBAL */
html, body, [class*="css"] {
    font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
}

/* PAGE BG */
.stApp {
    background:#0b0f19;
    color:#e5e7eb;
}

/* REMOVE STREAMLIT BLOCK BG */
section.main > div {
    background:transparent;
}

/* HEADER */
.title {
    font-size:40px;
    font-weight:600;
    text-align:center;
    margin-top:40px;
}
.subtitle {
    text-align:center;
    color:#9ca3af;
    margin-bottom:40px;
}

/* PANEL */
.panel {
    background:#111827;
    border:1px solid #1f2937;
    border-radius:12px;
    padding:24px;
    box-shadow:0 6px 20px rgba(0,0,0,.25);
}

/* BUTTON */
.primary-btn {
    background:#2563eb;
    border:none;
    color:white;
    padding:10px 22px;
    border-radius:8px;
    font-weight:500;
    text-decoration:none;
}
.primary-btn:hover {
    background:#1d4ed8;
}

/* METRIC */
.metric-box {
    background:#111827;
    border:1px solid #1f2937;
    border-radius:12px;
    padding:18px;
    text-align:center;
}
.metric-value {
    font-size:26px;
    font-weight:600;
}
.metric-label {
    color:#9ca3af;
    font-size:14px;
}

/* TABLE */
[data-testid="stDataFrame"] {
    border:1px solid #1f2937;
    border-radius:12px;
    overflow:hidden;
}

/* UPLOAD */
[data-testid="stFileUploader"] {
    border:1px dashed #374151;
    border-radius:12px;
    padding:20px;
    background:#0b0f19;
}

/* DIVIDER */
hr {
    border:0;
    border-top:1px solid #1f2937;
    margin:30px 0;
}

</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown('<div class="title">AI Data Cleaning Tool</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Upload messy CSV or Excel → get clean analysis-ready data instantly</div>', unsafe_allow_html=True)

# ---------- SESSION ----------
if "active_job" not in st.session_state:
    st.session_state.active_job=False

# ---------- UPLOAD ----------
with st.container():
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    file = st.file_uploader("Upload CSV or Excel", type=["csv","xlsx","xls"])
    start = st.button("Start Cleaning")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- API HELPERS ----------
def safe_get(url):
    try:
        return requests.get(url,timeout=5).json()
    except:
        return None

def safe_post(url,files):
    try:
        return requests.post(url,files=files,timeout=30)
    except:
        return None

# ---------- START ----------
if start and file:
    r = safe_post(f"{API}/upload",files={"file":(file.name,file.getvalue())})
    if r:
        st.session_state.active_job=True
    st.rerun()

# ---------- EMPTY ----------
if not st.session_state.active_job:
    st.stop()

# ---------- JOB ----------
job_data = safe_get(f"{API}/job")

if not job_data:
    st.stop()

jid,job=list(job_data.items())[0]

# ---------- PROCESSING ----------
if job["status"]=="processing":
    st.progress(60)
    st.info("Cleaning dataset…")
    time.sleep(1)
    st.rerun()

# ---------- DONE ----------
if job["status"]=="completed":

    st.session_state.active_job=False
    q=job["quality"]

    st.markdown("### Quality")

    c1,c2,c3,c4=st.columns(4)
    metrics=[("Overall",q["overall"]),("Completeness",q["completeness"]),("Uniqueness",q["uniqueness"]),("Validity",q["validity"])]

    for col,(label,val) in zip([c1,c2,c3,c4],metrics):
        col.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{val}%</div>
            <div class="metric-label">{label}</div>
        </div>
        """,unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### Cleaned Data")
    st.dataframe(pd.DataFrame(job["preview"]))

    st.markdown("---")

    st.markdown("### Cleaning Actions")
    st.dataframe(pd.DataFrame(job["actions"],columns=["Column","Type","Strategy"]))

    st.markdown("---")

    st.markdown("### Downloads")
    d1,d2=st.columns(2)
    d1.markdown(f'<a class="primary-btn" href="{API}/download/{jid}/xlsx">Download Excel</a>',unsafe_allow_html=True)
    d2.markdown(f'<a class="primary-btn" href="{API}/download/{jid}/csv">Download CSV</a>',unsafe_allow_html=True)

    st.markdown("---")

    b,a=st.columns(2)
    with b:
        st.markdown("**Before**")
        st.json(job["before"])
    with a:
        st.markdown("**After**")
        st.json(job["after"])
