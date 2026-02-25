# ============================
# AI DATA ENTRY ENTERPRISE
# FULL REAL FILE AI VERSION
# Single-file Fullstack System
# ============================

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import uvicorn, io, re, json, os
import pytesseract
from PIL import Image
import pdfplumber
import docx
import pandas as pd
from datetime import datetime

# ---------------------------
# AI MEMORY (FIELD LEARNING)
# ---------------------------
MEMORY_FILE = "field_memory.json"
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE,"w") as f:
        json.dump({},f)

def load_memory():
    with open(MEMORY_FILE,"r") as f:
        return json.load(f)

def save_memory(data):
    with open(MEMORY_FILE,"w") as f:
        json.dump(data,f,indent=4)

# ---------------------------
# APP INIT
# ---------------------------
app = FastAPI()

# ---------------------------
# OCR / FILE PARSERS
# ---------------------------
def extract_from_image(file_bytes):
    img = Image.open(io.BytesIO(file_bytes))
    text = pytesseract.image_to_string(img)
    return text

def extract_from_pdf(file_bytes):
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def extract_from_docx(file_bytes):
    doc = docx.Document(io.BytesIO(file_bytes))
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def extract_from_txt(file_bytes):
    return file_bytes.decode(errors="ignore")

# ---------------------------
# AI EXTRACTION ENGINE
# ---------------------------
def ai_extract(text):
    memory = load_memory()

    result = {
        "Persons": [],
        "PersonalDetails": {},
        "Address": {},
        "Financial": {},
        "Products": [],
        "Dates": {},
        "Transaction": {},
        "Notes": []
    }

    # ---------- HUMAN NAME FILTER ----------
    name_candidates = re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+', text)
    for n in name_candidates:
        if not any(x in n.lower() for x in ["road","street","office","company","technologies","city","state","country"]):
            if n not in result["Persons"]:
                result["Persons"].append(n)

    # ---------- AGE ----------
    ages = re.findall(r'(\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*) is (\d{1,3}) years', text)
    for name, age in ages:
        result["PersonalDetails"].setdefault(name,{})["Age"]=age

    # ---------- GENDER ----------
    if "male" in text.lower():
        for p in result["Persons"]:
            if "Gender" not in result["PersonalDetails"].get(p,{}):
                if p.lower() in text.lower():
                    result["PersonalDetails"].setdefault(p,{})["Gender"]="Male"

    # ---------- PHONE ----------
    phones = re.findall(r'\b\d{10}\b', text)
    if phones:
        result["Financial"]["Phones"]=phones

    # ---------- EMAIL ----------
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if emails:
        result["Financial"]["Emails"]=emails

    # ---------- ADDRESS ----------
    if "street" in text.lower():
        result["Address"]["Raw"]=re.findall(r'\d+.*,.*', text)

    # ---------- SALARY & AMOUNT ----------
    salaries = re.findall(r'salary is (\d+)', text.lower())
    if salaries:
        result["Financial"]["Salaries"]=salaries

    amounts = re.findall(r'amount paid.*?(\d+)', text.lower())
    if amounts:
        result["Financial"]["TotalAmount"]=amounts

    # ---------- PRODUCTS ----------
    products = re.findall(r'Product name is ([A-Za-z ]+).*?Quantity is (\d+).*?Price is (\d+)', text, re.S)
    for p in products:
        result["Products"].append({
            "Name":p[0].strip(),
            "Quantity":p[1],
            "Price":p[2]
        })

    # ---------- DATES ----------
    dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', text)
    if dates:
        if len(dates)>=1: result["Dates"]["Meeting"]=dates[0]
        if len(dates)>=2: result["Dates"]["FollowUp"]=dates[1]

    # ---------- TRANSACTION ----------
    txn = re.findall(r'TXN\d+', text)
    if txn:
        result["Transaction"]["Reference"]=txn[0]

    if "cash" in text.lower():
        result["Transaction"]["Mode"]="Cash"

    # ---------- NOTES ----------
    lines = text.split("\n")
    for l in lines:
        if "discussed" in l.lower() or "handled" in l.lower() or "managed" in l.lower():
            result["Notes"].append(l.strip())

    # ---------- FIELD LEARNING ----------
    for k in result:
        memory[k]=memory.get(k,0)+1
    save_memory(memory)

    return result

# ---------------------------
# API ROUTES
# ---------------------------
@app.post("/analyze")
async def analyze(file:UploadFile=None, text:str=Form(default="")):
    content = ""

    if file:
        data = await file.read()
        fname = file.filename.lower()

        if fname.endswith((".png",".jpg",".jpeg")):
            content = extract_from_image(data)
        elif fname.endswith(".pdf"):
            content = extract_from_pdf(data)
        elif fname.endswith(".docx"):
            content = extract_from_docx(data)
        elif fname.endswith(".txt"):
            content = extract_from_txt(data)
        else:
            content = data.decode(errors="ignore")

    if text:
        content += "\n"+text

    ai_data = ai_extract(content)
    return JSONResponse(ai_data)

@app.post("/export")
async def export(data:dict):
    rows=[]
    for k,v in data.items():
        rows.append({"Field":k,"Value":json.dumps(v,ensure_ascii=False)})
    df=pd.DataFrame(rows)
    file="export.xlsx"
    df.to_excel(file,index=False)
    return FileResponse(file,filename=file)

# ---------------------------
# FULLSTACK UI
# ---------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
<title>AI Data Entry Enterprise</title>
<style>
body{font-family:Arial;background:#f4f6f9;margin:0;padding:0}
.container{max-width:1200px;margin:auto;padding:20px}
.card{background:#fff;padding:20px;border-radius:10px;box-shadow:0 0 10px #ccc}
button{padding:10px 15px;border:none;border-radius:6px;background:#2563eb;color:#fff;cursor:pointer}
table{width:100%;border-collapse:collapse;margin-top:20px}
th,td{border:1px solid #ddd;padding:8px}
th{background:#f1f5f9}
input,textarea{width:100%;padding:10px;margin:5px 0}
</style>
</head>
<body>
<div class="container">
<div class="card">
<h2>AI Data Entry Enterprise</h2>

<input type="file" id="file">
<textarea id="text" placeholder="Paste text, message, notes..."></textarea>

<button onclick="analyze()">Analyze</button>
<button onclick="clearData()">Clear</button>
<button onclick="exportExcel()">Export Excel</button>

<h3>Extracted Data</h3>
<div id="output"></div>

</div>
</div>

<script>
let lastData=null;

function analyze(){
    let f=document.getElementById("file").files[0];
    let t=document.getElementById("text").value;
    let fd=new FormData();
    if(f)fd.append("file",f);
    fd.append("text",t);

    fetch("/analyze",{method:"POST",body:fd})
    .then(r=>r.json())
    .then(d=>{
        lastData=d;
        render(d);
    });
}

function render(d){
    let html="<table><tr><th>Field</th><th>Value</th></tr>";
    for(let k in d){
        html+=`<tr><td>${k}</td><td><pre>${JSON.stringify(d[k],null,2)}</pre></td></tr>`;
    }
    html+="</table>";
    document.getElementById("output").innerHTML=html;
}

function exportExcel(){
    if(!lastData){alert("No data");return;}
    fetch("/export",{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify(lastData)})
    .then(r=>r.blob())
    .then(b=>{
        let a=document.createElement("a");
        a.href=URL.createObjectURL(b);
        a.download="export.xlsx";
        a.click();
    });
}

function clearData(){
    document.getElementById("file").value="";
    document.getElementById("text").value="";
    document.getElementById("output").innerHTML="";
    lastData=null;
}
</script>
</body>
</html>
"""

# ---------------------------
# RUN
# ---------------------------
if __name__=="__main__":
    uvicorn.run(app,host="0.0.0.0",port=8000)
