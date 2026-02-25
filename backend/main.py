import os, re, io, json, uuid, datetime
from typing import Dict
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# ---------- SAFE IMPORTS ----------
try:
    import pytesseract
    from PIL import Image
except:
    pytesseract = None
    Image = None

try:
    import PyPDF2
except:
    PyPDF2 = None

try:
    import docx
except:
    docx = None

try:
    import pandas as pd
except:
    pd = None

# ---------- APP ----------
app = FastAPI(title="AI Data Entry Enterprise")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- MEMORY ----------
HISTORY = []
LAST_DATA = {}
FIELD_MEMORY = {}

# ---------- NLP FILTERS ----------
BLOCK_WORDS = [
    "ltd","pvt","company","street","road","nagar","colony","india","chennai",
    "bangalore","salem","district","state","pin","postcode","address","location"
]

NAME_REGEX = re.compile(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2}\b")
PHONE_REGEX = re.compile(r"\b[6-9]\d{9}\b")
EMAIL_REGEX = re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b")
AMOUNT_REGEX = re.compile(r"\b\d{3,}\b")
DATE_REGEX = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
PIN_REGEX = re.compile(r"\b\d{6}\b")

# ---------- AI ENGINE ----------
def clean_human_names(text):
    names = NAME_REGEX.findall(text)
    final = []
    for n in names:
        low = n.lower()
        if any(b in low for b in BLOCK_WORDS):
            continue
        if len(n.split()) > 3:
            continue
        if not all(w.isalpha() for w in n.replace(" ","")):
            continue
        final.append(n)
    return list(set(final))

def ai_extract(text:str)->Dict:
    data = {}

    names = clean_human_names(text)
    phones = PHONE_REGEX.findall(text)
    emails = EMAIL_REGEX.findall(text)
    amounts = AMOUNT_REGEX.findall(text)
    dates = DATE_REGEX.findall(text)
    pins = PIN_REGEX.findall(text)

    salary = []
    amount = []
    for a in amounts:
        try:
            if int(a) > 10000:
                salary.append(a)
            else:
                amount.append(a)
        except:
            pass

    data["Name"] = names
    data["Phone"] = list(set(phones))
    data["Email"] = list(set(emails))
    data["Salary"] = list(set(salary))
    data["Amount"] = list(set(amount))
    data["Date"] = list(set(dates))
    data["Pincode"] = list(set(pins))

    # auto learning
    for k,v in data.items():
        if k not in FIELD_MEMORY:
            FIELD_MEMORY[k] = set()
        for i in v:
            FIELD_MEMORY[k].add(i)

    return data

# ---------- FILE READERS ----------
def read_pdf(file:bytes):
    if not PyPDF2: return ""
    reader = PyPDF2.PdfReader(io.BytesIO(file))
    text = ""
    for p in reader.pages:
        t = p.extract_text()
        if t: text += t + "\n"
    return text

def read_docx(file:bytes):
    if not docx: return ""
    d = docx.Document(io.BytesIO(file))
    return "\n".join([p.text for p in d.paragraphs])

def read_image(file:bytes):
    if not pytesseract or not Image: return ""
    img = Image.open(io.BytesIO(file))
    return pytesseract.image_to_string(img)

# ---------- UI ----------
HTML_UI = """
<!DOCTYPE html>
<html>
<head>
<title>AI Data Entry Enterprise</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body{margin:0;font-family:Segoe UI;background:#0e1627;color:white}
header{background:#0b1220;padding:15px;text-align:center;font-size:22px;font-weight:600}
.container{max-width:1200px;margin:auto;padding:20px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.card{background:#121b2f;border-radius:12px;padding:20px;box-shadow:0 0 10px rgba(0,0,0,.4)}
textarea,input{width:100%;padding:12px;border-radius:8px;border:none;margin:8px 0}
button{padding:12px 18px;border-radius:8px;border:none;cursor:pointer;font-weight:600}
.btn{background:#00e5ff;color:#000}
.btn2{background:#6c5ce7;color:white}
.table{width:100%;border-collapse:collapse;margin-top:10px}
th,td{border-bottom:1px solid #2d3a5f;padding:10px;text-align:left}
th{color:#00e5ff}
@media(max-width:800px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>

<header>AI Data Entry – Automated Data Worker</header>

<div class="container">

<div class="grid">
<div class="card">
<h3>Upload / Input</h3>
<input type="file" id="file">
<textarea id="text" rows="8" placeholder="Paste text here..."></textarea>
<button class="btn" onclick="analyze()">Analyze</button>
<button class="btn2" onclick="exportExcel()">Export Excel</button>
</div>

<div class="card">
<h3>Extracted Data</h3>
<table class="table">
<thead><tr><th>Field</th><th>Values</th></tr></thead>
<tbody id="result"></tbody>
</table>
</div>
</div>

<div class="card">
<h3>Custom Field</h3>
<input id="cf_name" placeholder="Field name">
<input id="cf_val" placeholder="Value">
<button class="btn" onclick="addCustom()">Add Field</button>
</div>

</div>

<script>
async function analyze(){
    let text=document.getElementById("text").value;
    let file=document.getElementById("file").files[0];
    let fd=new FormData();
    fd.append("text",text);
    if(file) fd.append("file",file);

    let r=await fetch("/analyze",{method:"POST",body:fd});
    let j=await r.json();

    let res=document.getElementById("result");
    res.innerHTML="";
    for(let k in j.data){
        let tr=document.createElement("tr");
        tr.innerHTML=`<td>${k}</td><td>${j.data[k].join(", ")}</td>`;
        res.appendChild(tr);
    }
}

function addCustom(){
    let n=document.getElementById("cf_name").value;
    let v=document.getElementById("cf_val").value;
    if(!n||!v) return;
    let res=document.getElementById("result");
    let tr=document.createElement("tr");
    tr.innerHTML=`<td>${n}</td><td>${v}</td>`;
    res.appendChild(tr);
}

function exportExcel(){
    window.location.href="/export";
}
</script>

</body>
</html>
"""

# ---------- ROUTES ----------
@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_UI

@app.post("/analyze")
async def analyze(text:str=Form(""), file:UploadFile=File(None)):
    content = text or ""

    if file:
        raw = await file.read()
        fname = file.filename.lower()

        if fname.endswith(".pdf"):
            content += read_pdf(raw)
        elif fname.endswith(".docx"):
            content += read_docx(raw)
        elif fname.endswith((".png",".jpg",".jpeg",".webp")):
            content += read_image(raw)
        else:
            try:
                content += raw.decode(errors="ignore")
            except:
                pass

    data = ai_extract(content)

    global LAST_DATA
    LAST_DATA = data

    ts = datetime.datetime.utcnow().isoformat()
    HISTORY.append(ts)
    if len(HISTORY)>10: HISTORY.pop(0)

    return {"data":data,"history":HISTORY}

@app.get("/export")
def export_excel():
    if not pd or not LAST_DATA:
        return JSONResponse({"error":"No data to export"})
    rows=[]
    for k,v in LAST_DATA.items():
        for item in v:
            rows.append({"Field":k,"Value":item})
    df=pd.DataFrame(rows)
    buf=io.BytesIO()
    df.to_excel(buf,index=False)
    buf.seek(0)
    return StreamingResponse(buf,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":"attachment; filename=extracted_data.xlsx"})
