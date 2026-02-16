import streamlit as st
import requests
import time
import pandas as pd

API ="https://ai-data-cleaning-tool.onrender.com"

# ---------- SESSION ----------
if "active_job" not in st.session_state:
    st.session_state.active_job = None

# ---------- PAGE ----------
st.set_page_config(
    page_title="AI Data Cleaning Tool",
    layout="centered",
)

# ---------- STYLE ----------
st.markdown("""
<style>

.block-container {
    max-width: 820px;
    padding-top: 3rem;
}

h1 {
    font-size: 42px !important;
    font-weight: 700;
    letter-spacing: -0.5px;
    text-align: center;
}

.subtitle {
    text-align: center;
    color: #6b7280;
    font-size: 18px;
    margin-bottom: 40px;
}

.section {
    margin-top: 40px;
}

.stButton > button {
    border-radius: 8px;
    padding: 10px 22px;
    font-weight: 600;
}

.primary button {
    background: black;
    color: white;
    border: none;
}

.secondary button {
    background: transparent;
    border: 1px solid #d1d5db;
    color: #111827;
}

.metric-card {
    text-align: center;
}

</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown("<h1>AI Data Cleaning Tool</h1>", unsafe_allow_html=True)
st.markdown(
    "<div class='subtitle'>Upload messy CSV or Excel → get clean analysis-ready data instantly</div>",
    unsafe_allow_html=True,
)

# ---------- SAFE REQUEST ----------
def safe_get(url):
    try:
        return requests.get(url, timeout=3).json()
    except:
        return None

def safe_post(url, files=None):
    try:
        return requests.post(url, files=files, timeout=10)
    except:
        return None

# ---------- UPLOAD ----------
st.markdown("<div class='section'></div>", unsafe_allow_html=True)

file = st.file_uploader("Upload CSV or Excel", type=["csv","xlsx","xls"])

c1, c2 = st.columns(2)

with c1:
    st.markdown("<div class='primary'>", unsafe_allow_html=True)
    start = st.button("Start Cleaning")
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='secondary'>", unsafe_allow_html=True)
    reset = st.button("New Upload")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- ACTIONS ----------
if start and file:
    res = safe_post(f"{API}/upload", files={"file": (file.name, file.getvalue())})
    if res:
        st.session_state.active_job = res.json()["job_id"]
    st.rerun()

if reset:
    requests.post(f"{API}/reset")
    st.session_state.active_job = None
    st.rerun()

# ---------- JOB ----------
job_data = safe_get(f"{API}/job")

if not job_data or st.session_state.active_job is None:
    st.info("Upload dataset to start")
    st.stop()

jid, job = list(job_data.items())[0]

if jid != st.session_state.active_job:
    st.info("Upload dataset to start")
    st.stop()

# ---------- PROCESS ----------
if job["status"] == "processing":
    st.warning("Cleaning data…")
    st.progress(60)
    time.sleep(0.8)
    st.rerun()

# ---------- RESULTS ----------
if job["status"] == "completed":

    q = job["quality"]

    st.markdown("<div class='section'></div>", unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Overall", f"{q['overall']}%")
    m2.metric("Completeness", f"{q['completeness']}%")
    m3.metric("Uniqueness", f"{q['uniqueness']}%")
    m4.metric("Validity", f"{q['validity']}%")

    st.markdown("<div class='section'></div>", unsafe_allow_html=True)
    st.subheader("Cleaned Data Preview")

    st.dataframe(pd.DataFrame(job["preview"]), use_container_width=True)

    st.markdown("<div class='section'></div>", unsafe_allow_html=True)
    st.subheader("Cleaning Actions")

    st.dataframe(
        pd.DataFrame(job["actions"], columns=["Column","Type","Strategy"]),
        use_container_width=True,
    )

    st.markdown("<div class='section'></div>", unsafe_allow_html=True)
    st.subheader("Downloads")

    d1, d2 = st.columns(2)

    d1.link_button("Download Excel", f"{API}/download/{jid}/xlsx")
    d2.link_button("Download CSV", f"{API}/download/{jid}/csv")

    st.markdown("<div class='section'></div>", unsafe_allow_html=True)
    st.subheader("Before vs After")

    b, a = st.columns(2)

    b.json(job["before"])
    a.json(job["after"])
