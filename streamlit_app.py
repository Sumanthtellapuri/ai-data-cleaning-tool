import streamlit as st
import requests
import time
import pandas as pd

API="https://ai-data-cleaning-tool.onrender.com"

st.set_page_config(page_title="AI Data Cleaning Tool", layout="wide")

# ---------- SESSION ----------
if "active_job" not in st.session_state:
    st.session_state.active_job = False

# ---------- STYLE ----------
st.markdown("""
<style>
.big-title{
font-size:48px;
font-weight:700;
text-align:center;
margin-top:20px;
}
.subtitle{
text-align:center;
color:#6b7280;
margin-bottom:40px;
}
.card{
background:#0f172a;
padding:20px;
border-radius:16px;
text-align:center;
box-shadow:0 10px 30px rgba(0,0,0,0.25);
}
.metric{
font-size:28px;
font-weight:700;
}
.label{
color:#94a3b8;
}
.primary-btn{
background:linear-gradient(90deg,#924f72,#000000);
padding:14px 34px;
border-radius:999px;
color:white;
font-weight:600;
text-align:center;
display:inline-block;
margin-top:10px;
}
</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown('<div class="big-title">AI Data Cleaning Tool</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Automatic CSV & Excel cleaning with smart imputation and quality scoring</div>', unsafe_allow_html=True)

# ---------- UPLOAD ----------
file = st.file_uploader("Upload CSV or Excel", type=["csv","xlsx","xls"])

start = st.button("Start Cleaning")

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
    st.info("Upload dataset to start")
    st.stop()

# ---------- JOB ----------
job_data = safe_get(f"{API}/job")

if not job_data:
    st.info("Waiting for processing")
    st.stop()

jid,job=list(job_data.items())[0]

# ---------- PROCESSING ----------
if job["status"]=="processing":
    st.progress(60)
    st.warning("Cleaning intelligently…")
    time.sleep(1)
    st.rerun()

# ---------- COMPLETED ----------
if job["status"]=="completed":

    st.session_state.active_job=False

    q=job["quality"]

    c1,c2,c3,c4=st.columns(4)

    for c,val,label in zip(
        [c1,c2,c3,c4],
        [q["overall"],q["completeness"],q["uniqueness"],q["validity"]],
        ["Overall","Completeness","Uniqueness","Validity"]
    ):
        c.markdown(f"""
        <div class="card">
            <div class="metric">{val}%</div>
            <div class="label">{label}</div>
        </div>
        """,unsafe_allow_html=True)

    st.markdown("### Cleaned Data Preview")
    st.dataframe(pd.DataFrame(job["preview"]))

    st.markdown("### Cleaning Actions")
    st.dataframe(pd.DataFrame(job["actions"],columns=["Column","Type","Strategy"]))

    st.markdown("### Downloads")
    d1,d2=st.columns(2)
    d1.markdown(f'<a class="primary-btn" href="{API}/download/{jid}/xlsx">Download Excel</a>',unsafe_allow_html=True)
    d2.markdown(f'<a class="primary-btn" href="{API}/download/{jid}/csv">Download CSV</a>',unsafe_allow_html=True)

    st.markdown("### Before vs After")
    b,a=st.columns(2)
    b.json(job["before"])
    a.json(job["after"])
