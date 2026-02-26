import os
import io
import json
import base64
import tempfile
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from PIL import Image
import pytesseract
import pdfplumber
import docx
import pandas as pd

# ================= CONFIG =================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-flash")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HISTORY = []
LAST_ANALYSIS = {}

# ================= AI PROMPT =================
SYSTEM_PROMPT = """
You are an enterprise AI data extraction engine.

TASK:
Extract structured data from unstructured input text.

RULES:
- Extract HUMAN NAMES ONLY in Persons
- Do NOT include company names, locations, places as persons
- Separate Phone and Alternate Phone
- Multiple values allowed
- Salary only numeric
- Amount only numeric
- Products grouped
- Dates grouped
- Notes grouped
- Address structured
- Transactions structured
- JSON output ONLY
- No explanations
- No markdown
- No text outside JSON

OUTPUT FORMAT STRICT JSON:

{
  "Persons": [],
  "PersonalDetails": {},
  "AddressDetails": {},
  "FinancialInformation": {},
  "ProductPurchaseDetails": [],
  "Dates": {},
  "TransactionDetails": {},
  "Notes": [],
  "CustomFields": {}
}
"""

# ================= UTIL FUNCTIONS =================
def gemini_analyze(text: str):
    prompt = SYSTEM_PROMPT + "\n\nINPUT:\n" + text
    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Clean markdown if any
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(raw)
    except:
        data = {"error": "AI_PARSE_ERROR", "raw": raw}

    return data


def extract_text_from_file(file: UploadFile):
    name = file.filename.lower()

    if name.endswith((".png", ".jpg", ".jpeg")):
        image = Image.open(file.file)
        return pytesseract.image_to_string(image)

    elif name.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file.file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    elif name.endswith(".docx"):
        doc = docx.Document(file.file)
        return "\n".join([p.text for p in doc.paragraphs])

    elif name.endswith(".txt"):
        return file.file.read().decode("utf-8")

    else:
        return ""

# ================= FRONTEND =================
@app.get("/", response_class=HTMLResponse)
def ui():
    return """
<!DOCTYPE html>
<html>
<head>
<title>AI Data Entry Enterprise</title>
<style>
body{font-family:Arial;background:#0f172a;color:#fff;margin:0}
.container{max-width:1400px;margin:auto;padding:20px}
.card{background:#111827;border-radius:12px;padding:20px;margin-bottom:15px}
textarea,input,button{width:100%;padding:10px;margin:5px 0;border-radius:6px;border:none}
button{background:#2563eb;color:#fff;font-weight:bold;cursor:pointer}
button:hover{background:#1d4ed8}
table{width:100%;border-collapse:collapse;margin-top:10px}
th,td{border:1px solid #334155;padding:8px}
th{background:#1e293b}
.section{margin-top:20px}
.flex{display:flex;gap:10px}
</style>
</head>
<body>
<div class="container">
<h1>AI Data Entry Enterprise System</h1>

<div class="card">
<h3>Input Text</h3>
<textarea id="text" rows="8"></textarea>

<div class="flex">
<input type="file" id="file"/>
<button onclick="analyze()">Analyze</button>
<button onclick="clearAll()">Clear</button>
<button onclick="exportExcel()">Export Excel</button>
</div>
</div>

<div class="card">
<h3>Custom Field</h3>
<input id="cfield" placeholder="Field Name"/>
<input id="cvalue" placeholder="Field Value"/>
<button onclick="addCustom()">Add Custom Field</button>
</div>

<div class="card">
<h3>Extracted Data</h3>
<pre id="output"></pre>
</div>

</div>

<script>
let extracted = {}

async function analyze(){
    let text = document.getElementById("text").value
    let file = document.getElementById("file").files[0]

    let fd = new FormData()
    fd.append("text", text)
    if(file) fd.append("file", file)

    let res = await fetch("/analyze",{method:"POST",body:fd})
    let data = await res.json()
    extracted = data
    document.getElementById("output").innerText = JSON.stringify(data,null,2)
}

function clearAll(){
    document.getElementById("text").value=""
    document.getElementById("output").innerText=""
    extracted={}
}

async function exportExcel(){
    let res = await fetch("/export",{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify(extracted)})
    let blob = await res.blob()
    let a = document.createElement("a")
    a.href = URL.createObjectURL(blob)
    a.download = "ai_data.xlsx"
    a.click()
}

function addCustom(){
    let f = document.getElementById("cfield").value
    let v = document.getElementById("cvalue").value
    if(!extracted.CustomFields) extracted.CustomFields={}
    extracted.CustomFields[f]=v
    document.getElementById("output").innerText = JSON.stringify(extracted,null,2)
}
</script>
</body>
</html>
"""

# ================= API =================
@app.post("/analyze")
async def analyze(text: str = Form(""), file: UploadFile = File(None)):
    content = text or ""
    if file:
        content += "\n" + extract_text_from_file(file)

    ai_data = gemini_analyze(content)

    HISTORY.append(ai_data)
    global LAST_ANALYSIS
    LAST_ANALYSIS = ai_data

    return JSONResponse(ai_data)


@app.post("/export")
async def export_excel(data: dict):
    rows = []

    def flatten(prefix, obj):
        if isinstance(obj, dict):
            for k,v in obj.items():
                flatten(f"{prefix}.{k}" if prefix else k, v)
        elif isinstance(obj, list):
            for i,v in enumerate(obj):
                flatten(f"{prefix}[{i}]", v)
        else:
            rows.append({"Field":prefix,"Value":obj})

    flatten("", data)

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_excel(buf,index=False)
    buf.seek(0)

    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":"attachment; filename=ai_data.xlsx"})
