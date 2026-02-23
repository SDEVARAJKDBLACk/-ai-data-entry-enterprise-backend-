from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import requests
import pandas as pd
import sqlite3
import os
import json
from datetime import datetime

# ================= CONFIG =================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Set in Render env
DB_FILE = "history.db"
EXPORT_FILE = "export.xlsx"

# ================= APP =================
app = FastAPI(title="AI Data Entry Enterprise API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_text TEXT,
            ai_result TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ================= UTILS =================
def save_history(raw, ai_result):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO history (raw_text, ai_result, created_at) VALUES (?,?,?)",
        (raw, json.dumps(ai_result), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def call_openai(prompt: str):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are an AI data extraction engine. Detect fields, map data, return JSON only."},
            {"role": "user", "content": prompt}
        ]
    }

    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
    data = r.json()
    text = data["choices"][0]["message"]["content"]
    return text

# ================= API =================

@app.get("/")
def root():
    return {"status": "AI Data Entry Enterprise Backend Running"}

@app.post("/analyze")
async def analyze_data(payload: dict):
    raw_text = payload.get("text", "")

    ai_prompt = f"""
    Analyze the following data.
    Tasks:
    - Detect fields
    - Map values
    - Auto-create fields
    - Return JSON
    - Unlimited fields
    - Include 20 core fields if possible
    Data:
    {raw_text}
    """

    ai_response = call_openai(ai_prompt)

    try:
        ai_json = json.loads(ai_response)
    except:
        ai_json = {"raw_ai_output": ai_response}

    save_history(raw_text, ai_json)

    return {
        "success": True,
        "data": ai_json
    }

@app.get("/history")
def get_history():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, raw_text, ai_result, created_at FROM history ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "raw_text": r[1],
            "ai_result": json.loads(r[2]),
            "created_at": r[3]
        })

    return result

@app.get("/export")
def export_excel():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM history", conn)
    conn.close()

    df.to_excel(EXPORT_FILE, index=False)
    return FileResponse(EXPORT_FILE, filename="ai_data_entry_export.xlsx")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode(errors="ignore")

    ai_prompt = f"""
    Extract structured data from this document text.
    Detect fields, auto-map values, return JSON.
    Text:
    {text}
    """

    ai_response = call_openai(ai_prompt)

    try:
        ai_json = json.loads(ai_response)
    except:
        ai_json = {"raw_ai_output": ai_response}

    save_history(text, ai_json)

    return {"success": True, "data": ai_json}

# ===== Cloud OCR Placeholder (Production Safe) =====
@app.post("/ocr")
async def cloud_ocr_stub():
    return {
        "status": "OCR not enabled",
        "message": "Cloud OCR will be integrated (Google Vision / Azure / AWS Textract)"
    }
