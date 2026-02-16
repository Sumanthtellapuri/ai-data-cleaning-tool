from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import numpy as np
import os
import uuid
import threading
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
def quality(df):
    total = df.size
    missing = df.isnull().sum().sum()
    dup = df.duplicated().sum()

    completeness = 100 - int((missing/total)*100)
    uniqueness = 100 - int((dup/len(df))*100)
    validity = completeness
    overall = int((completeness+uniqueness+validity)/3)

    return {
        "overall":overall,
        "completeness":completeness,
        "uniqueness":uniqueness,
        "validity":validity
    }

# ---------- CLEAN ----------
def clean_df(df):

    actions = []
    df = df.drop_duplicates()

    for col in df.columns:
        s = df[col]

        if pd.api.types.is_numeric_dtype(s):
            med = s.median()
            df[col] = s.fillna(med)
            actions.append((col,"Numeric","Median fill"))

        else:
            mode = s.mode().iloc[0] if not s.mode().empty else "Unknown"
            df[col] = s.fillna(mode)
            actions.append((col,"Categorical","Mode fill"))

    return df, actions

# ---------- PROCESS ----------
def process(job_id, path, name):

    start = time.time()

    try:
        if path.endswith(".csv"):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)

        before = profile(df)

        cleaned, actions = clean_df(df)

        after = profile(cleaned)
        q = quality(cleaned)

        preview = cleaned.head(20).to_dict(orient="records")

        xlsx = f"{CLEANED_DIR}/{job_id}.xlsx"
        csv = f"{CLEANED_DIR}/{job_id}.csv"

        cleaned.to_excel(xlsx,index=False)
        cleaned.to_csv(csv,index=False)

        job_store[job_id].update({
            "status":"completed",
            "filename":name,
            "before":before,
            "after":after,
            "quality":q,
            "actions":actions,
            "preview":preview,
            "duration":round(time.time()-start,2)
        })

    except Exception as e:
        job_store[job_id]["status"]="failed"
        job_store[job_id]["error"]=str(e)

# ---------- RESET ----------
def clear_jobs():
    job_store.clear()

# ---------- UPLOAD ----------
@app.post("/upload")
async def upload(file: UploadFile = File(...)):

    clear_jobs()

    job_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    path = f"{UPLOAD_DIR}/{job_id}{ext}"

    with open(path,"wb") as f:
        f.write(await file.read())

    job_store[job_id] = {
        "status":"processing",
        "filename":file.filename,
        "path":path
    }

    t = threading.Thread(target=process,args=(job_id,path,file.filename))
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
        return FileResponse(path, filename=f"cleaned.{fmt}")
    return {"error":"not ready"}
