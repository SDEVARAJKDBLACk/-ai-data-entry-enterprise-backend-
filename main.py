
import os, openai, json, sqlite3, uuid
import pytesseract, fitz, pandas as pd
from PIL import Image
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="AI Data Entry Enterprise")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "history.db"

def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS history(id TEXT, input TEXT, result TEXT)")
    con.commit()
    con.close()

init_db()

def ocr_image(file):
    img = Image.open(file)
    return pytesseract.image_to_string(img)

def read_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

@app.get("/")
def root():
    return {"status":"AI Data Entry Backend Running"}

@app.post("/analyze")
async def analyze(text:str = Form(""), file:UploadFile = File(None)):
    raw = text
    if file:
        if file.filename.endswith(".pdf"):
            raw += read_pdf(file.file)
        elif file.filename.lower().endswith((".png",".jpg",".jpeg")):
            raw += ocr_image(file.file)

    prompt = f"Extract structured fields and return JSON only:\n{raw}"

    res = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    result = res["choices"][0]["message"]["content"]
    hid = str(uuid.uuid4())

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("INSERT INTO history VALUES(?,?,?)",(hid,raw,result))
    con.commit()
    con.close()

    return {"id":hid,"data":result}

@app.get("/history")
def history():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT * FROM history")
    rows = cur.fetchall()
    con.close()
    return rows

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
