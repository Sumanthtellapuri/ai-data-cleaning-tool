from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import numpy as np
import os
import uuid
import threading
import time
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def root():
    return {"status": "AI Data Cleaning API running"}

UPLOAD_DIR = "uploads"
CLEANED_DIR = "cleaned"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CLEANED_DIR, exist_ok=True)

job_store = {}

# ---------- PROFILE ----------
def profile(df):
    return {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "missing_values": df.isnull().sum().to_dict(),
        "duplicate_rows": int(df.duplicated().sum())
    }

# ---------- QUALITY ----------
def quality_breakdown(df):
    total_cells = df.size
    missing = df.isnull().sum().sum()
    duplicates = df.duplicated().sum()

    completeness = 100 - int((missing / total_cells) * 100)
    uniqueness = 100 - int((duplicates / len(df)) * 100)
    validity = completeness

    overall = int((completeness + uniqueness + validity) / 3)

    return {
        "overall": overall,
        "completeness": completeness,
        "uniqueness": uniqueness,
        "validity": validity
    }

# ---------- ANOMALY ----------
def detect_anomalies(df):
    anomalies = {}

    for col in df.select_dtypes(include=[np.number]).columns:
        s = df[col].dropna()
        if len(s) < 5:
            continue

        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1

        outliers = s[(s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)]

        if "age" in col.lower():
            impossible = s[(s < 0) | (s > 120)]
            outliers = pd.concat([outliers, impossible])

        if "salary" in col.lower() or "price" in col.lower():
            impossible = s[s < 0]
            outliers = pd.concat([outliers, impossible])

        if len(outliers) > 0:
            anomalies[col] = int(len(outliers))

    return anomalies

# ---------- IDENTIFIER ----------
def is_identifier(col, series):
    name = col.lower()
    if "id" in name or "code" in name or "number" in name:
        return True
    if series.nunique() == len(series):
        return True
    return False

# ---------- TYPE DETECT ----------
def detect_type(series):
    s = series.dropna().astype(str)

    if s.empty:
        return "categorical"

    try:
        pd.to_numeric(s.str.replace(",", ""))
        return "numeric"
    except:
        pass

    vals = s.str.lower().unique()

    if set(vals).issubset({"m","male","f","female"}):
        return "gender"

    if set(vals).issubset({"y","yes","n","no","true","false"}):
        return "boolean"

    if any(re.search(r"\d{4}", v) for v in vals):
        return "date"

    return "categorical"

# ---------- NORMALIZE ----------
def normalize_gender(series):
    m = {"m":"Male","male":"Male","f":"Female","female":"Female"}
    return series.astype(str).str.lower().map(m).fillna(series)

def normalize_bool(series):
    m = {"y":"Yes","yes":"Yes","true":"Yes",
         "n":"No","no":"No","false":"No"}
    return series.astype(str).str.lower().map(m).fillna(series)

def normalize_numeric(series):
    s = pd.to_numeric(series.astype(str).str.replace(",",""), errors="coerce")
    s = s.replace({0:np.nan,999:np.nan,-1:np.nan})
    return s

def normalize_date(series):
    return pd.to_datetime(series, errors="coerce")

def normalize_text(series):
    return series.astype(str).str.strip().str.title()

# ---------- SMART IMPUTE ----------
def smart_impute(df):

    actions = []
    types = {}

    df = df.drop_duplicates()

    for col in df.columns:

        series = df[col]
        col_type = detect_type(series)
        types[col] = col_type

        if is_identifier(col, series):
            actions.append((col, "Identifier", "Untouched"))
            continue

        if col_type == "numeric":
            s = normalize_numeric(series)
            val = s.median()
            df[col] = s.fillna(val)
            actions.append((col, "Numeric", "Median fill"))

        elif col_type == "gender":
            s = normalize_gender(series)
            df[col] = s.fillna("Unknown")
            actions.append((col, "Gender", "Normalized"))

        elif col_type == "boolean":
            s = normalize_bool(series)
            mode = s.mode().iloc[0] if not s.mode().empty else "No"
            df[col] = s.fillna(mode)
            actions.append((col, "Boolean", "Mode fill"))

        elif col_type == "date":
            s = normalize_date(series)
            df[col] = s.interpolate()
            actions.append((col, "Date", "Interpolated"))

        else:
            s = normalize_text(series)
            mode = s.mode().iloc[0] if not s.mode().empty else "Unknown"
            df[col] = s.fillna(mode)
            actions.append((col, "Categorical", "Mode fill"))

    return df, actions, types

# ---------- PROCESS ----------
def process_file(job_id, file_path, filename):

    start = time.time()

    try:
        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        before = profile(df)

        cleaned, actions, types = smart_impute(df)
        after = profile(cleaned)

        anomalies = detect_anomalies(cleaned)
        quality = quality_breakdown(cleaned)

        preview = cleaned.head(10).to_dict(orient="records")

        excel_path = f"{CLEANED_DIR}/{job_id}.xlsx"
        csv_path = f"{CLEANED_DIR}/{job_id}.csv"

        cleaned.to_excel(excel_path, index=False)
        cleaned.to_csv(csv_path, index=False)

        job_store[job_id].update({
            "status":"completed",
            "filename":filename,
            "before":before,
            "after":after,
            "quality":quality,
            "actions":actions,
            "types":types,
            "preview":preview,
            "anomalies": anomalies,
            "duration":round(time.time()-start,2)
        })

    except Exception as e:
        job_store[job_id]["status"]="failed"
        job_store[job_id]["error"]=str(e)

# ---------- UPLOAD ----------
@app.post("/upload")
async def upload(file: UploadFile = File(...)):

    job_store.clear()

    job_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    path = f"{UPLOAD_DIR}/{job_id}{ext}"

    with open(path,"wb") as f:
        f.write(await file.read())

    job_store[job_id]={"status":"processing","filename":file.filename,"path":path}

    t = threading.Thread(target=process_file,args=(job_id,path,file.filename))
    t.start()

    return {"job_id":job_id}

# ---------- JOB ----------
@app.get("/job")
def job():
    if not job_store:
        return {}
    jid,job=list(job_store.items())[0]
    return {jid:job}

# ---------- DOWNLOAD ----------
@app.get("/download/{job_id}/{fmt}")
def download(job_id:str, fmt:str):
    path=f"{CLEANED_DIR}/{job_id}.{fmt}"
    if os.path.exists(path):
        return FileResponse(path,filename=f"cleaned.{fmt}")
    return {"error":"not ready"}
