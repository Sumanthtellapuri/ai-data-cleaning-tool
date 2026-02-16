import streamlit as st
import requests
import pandas as pd
import time

API = "https://ai-data-cleaning-tool.onrender.com"

st.set_page_config(page_title="AI Data Cleaning Tool", layout="wide")

# ---------- GLOBAL STYLE ----------
st.markdown("""
<style>

/* base */
html, body, [class*="css"] {
    font-family: Inter, sans-serif;
    background:#030712;
    color:#e2e8f0;
}

/* remove ALL streamlit borders & lines */
section.main > div {
    border:none !important;
}

[data-testid="stHorizontalBlock"] > div {
    border:none !important;
}

hr {
    display:none;
}

.block-container {
    padding-top:2rem;
}

/* remove dataframe grid lines */
[data-testid="stDataFrame"] table {
    border-collapse:separate !important;
    border-spacing:0 !important;
}

[data-testid="stDataFrame"] th,
[data-testid="stDataFrame"] td {
    border:none !important;
}

/* glass card */
.glass {
    background: rgba(255,255,255,0.03);
    border:1px solid rgba(255,255,255,0.06);
    border-radius:18px;
    padding:22px;
    backdrop-filter: blur(10px);
    margin-bottom:24px;
}

/* gradient button */
.stButton>button {
    background: linear-gradient(90deg,#6366f1,#22d3ee);
    color:white;
    border:none;
    border-radius:999px;
    padding:10px 28px;
    font-weight:600;
    transition:.25s;
}
.stButton>button:hover {
    transform:translateY(-1px);
    box-shadow:0 8px 24px #6366f155;
}

/* metrics */
.metric {
    background: rgba(255,255,255,0.03);
    border:1px solid rgba(255,255,255,0.06);
    border-radius:16px;
    padding:18px;
    text-align:center;
}

/* remove json borders */
[data-testid="stJson"] {
    background: transparent !important;
    border:none !important;
}

/* remove container lines */
div[data-testid="stVerticalBlock"] > div {
    border:none !important;
}

</style>
""", unsafe_allow_html=True)

# ---------- HERO ----------
st.markdown("""
<h1 style='text-align:center;
background:linear-gradient(90deg,#fff,#a5b4fc,#22d3ee);
-webkit-background-clip:text;
-webkit-text-fill-color:transparent;
font-size:48px;
margin-bottom:8px;'>
AI Data Cleaning Tool
</h1>

<p style='text-align:center;color:#94a3b8;margin-bottom:40px;font-size:18px;'>
Automatic CSV & Excel cleaning with anomaly detection,
smart imputation and quality scoring.
</p>
""", unsafe_allow_html=True)

# ---------- REQUEST ----------
def safe_get(url):
    try:
        return requests.get(url, timeout=3).json()
    except:
        return None

def safe_post(url, files=None):
    try:
        return requests.post(url, files=files, timeout=30)
    except:
        return None

# ---------- UPLOAD ----------
st.markdown("<div class='glass'>", unsafe_allow_html=True)
file = st.file_uploader("Upload CSV or Excel", type=["csv","xlsx","xls"])

center = st.columns([1,2,1])[1]
with center:
    start = st.button("Start Cleaning")

st.markdown("</div>", unsafe_allow_html=True)

if start and file:
    safe_post(f"{API}/upload", files={"file":(file.name,file.getvalue())})
    st.rerun()

# ---------- JOB ----------
job_data = safe_get(f"{API}/job")

if job_data is None:
    st.error("Backend not running")
    st.stop()

if not job_data:
    st.info("Upload dataset to start")
    st.stop()

jid, job = list(job_data.items())[0]

# ---------- PROCESS ----------
if job["status"] == "processing":
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.progress(50)
    st.markdown("<center>AI is cleaning your dataset…</center>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    time.sleep(0.8)
    st.rerun()

# ---------- RESULTS ----------
if job["status"] == "completed":

    q = job["quality"]

    m1,m2,m3,m4 = st.columns(4)
    with m1:
        st.markdown(f"<div class='metric'><b>Overall</b><br>{q['overall']}%</div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric'><b>Completeness</b><br>{q['completeness']}%</div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='metric'><b>Uniqueness</b><br>{q['uniqueness']}%</div>", unsafe_allow_html=True)
    with m4:
        st.markdown(f"<div class='metric'><b>Validity</b><br>{q['validity']}%</div>", unsafe_allow_html=True)

    # preview
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.subheader("Cleaned Data Preview")
    st.dataframe(pd.DataFrame(job["preview"]), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # types
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.subheader("Column Types")
    st.json(job["types"])
    st.markdown("</div>", unsafe_allow_html=True)

    # actions
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.subheader("Cleaning Actions")
    df = pd.DataFrame(job["actions"], columns=["Column","Type","Strategy"])
    st.dataframe(df, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # downloads
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.subheader("Downloads")
    d1,d2 = st.columns(2)
    d1.markdown(f"[Download Excel]({API}/download/{jid}/xlsx)")
    d2.markdown(f"[Download CSV]({API}/download/{jid}/csv)")
    st.markdown("</div>", unsafe_allow_html=True)

    # before after
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.subheader("Before vs After")
    b,a = st.columns(2)
    with b:
        st.json(job["before"])
    with a:
        st.json(job["after"])
    st.markdown("</div>", unsafe_allow_html=True)
