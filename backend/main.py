import os, json, uuid, sqlite3
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
from PIL import Image
import pytesseract
import fitz  # PyMuPDF
import pandas as pd
import openai

# ---------------- CONFIG ----------------
openai.api_key = os.getenv("OPENAI_API_KEY")
DB = "history.db"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DB INIT ----------------
def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS history(
            id TEXT,
            input TEXT,
            result TEXT
        )
    """)
    con.commit()
    con.close()

init_db()

# ---------------- HELPERS ----------------
def save_history(raw, result):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("INSERT INTO history VALUES(?,?,?)", (
        str(uuid.uuid4()), raw, json.dumps(result)
    ))
    con.commit()
    con.close()


def ocr_image(file):
    img = Image.open(file)
    return pytesseract.image_to_string(img)


def read_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text


# ---------------- ROUTES ----------------
@app.get("/")
def root():
    return {"status": "AI Data Entry Backend Running"}


@app.post("/analyze")
async def analyze(text: str = Form(""), file: UploadFile = File(None)):
    raw_text = text

    if file:
        if file.filename.lower().endswith(".pdf"):
            raw_text += read_pdf(file.file)
        elif file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            raw_text += ocr_image(file.file)

    prompt = f"""
    Extract structured fields from this data.
    Auto detect fields.
    Return clean JSON only.

    DATA:
    {raw_text}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a data extraction AI"},
            {"role": "user", "content": prompt}
        ]
    )

    result_text = response["choices"][0]["message"]["content"]

    try:
        result_json = json.loads(result_text)
    except:
        result_json = {"raw": result_text}

    save_history(raw_text, result_json)

    return result_json


@app.get("/history")
def history():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT * FROM history ORDER BY rowid DESC LIMIT 10")
    rows = cur.fetchall()
    con.close()

    return [{"id": r[0], "input": r[1], "result": json.loads(r[2])} for r in rows]


@app.get("/export")
def export_excel():
    con = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM history", con)
    con.close()

    file = "export.xlsx"
    df.to_excel(file, index=False)
    return FileResponse(file, filename="ai_data_export.xlsx")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
