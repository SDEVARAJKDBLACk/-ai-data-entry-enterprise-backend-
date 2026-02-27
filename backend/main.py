import os, io, json, re, uuid
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from PIL import Image
import PyPDF2
import docx
import pandas as pd

# ================= CONFIG =================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

text_model = genai.GenerativeModel("gemini-1.5-flash")
vision_model = genai.GenerativeModel("gemini-1.5-flash")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_STORE = {}
LAST_ANALYSIS = {}

# ================= UTILS =================

def extract_text_from_file(file: UploadFile, content: bytes):
    name = file.filename.lower()
    if name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        return "\n".join([p.extract_text() or "" for p in reader.pages])
    elif name.endswith(".docx"):
        d = docx.Document(io.BytesIO(content))
        return "\n".join([p.text for p in d.paragraphs])
    elif name.endswith((".txt", ".md")):
        return content.decode(errors="ignore")
    elif name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        img = Image.open(io.BytesIO(content))
        return img
    else:
        return content.decode(errors="ignore")

def gemini_analyze(text: str):
    prompt = f"""
You are an AI data extraction engine.
Extract structured data in JSON format only.

Rules:
- Persons: human names only
- Separate phone and alternate phone
- Amount field: salary, amount, price only
- Multiple values allowed per field
- Strict JSON

Text:
{text}
"""
    res = text_model.generate_content(prompt)
    raw = res.text.strip()
    raw = re.sub(r"```json|```", "", raw)
    return json.loads(raw)

def gemini_image_analyze(image: Image.Image):
    prompt = """
Extract all meaningful structured data from this image.
Return only JSON.
"""
    res = vision_model.generate_content([prompt, image])
    raw = res.text.strip()
    raw = re.sub(r"```json|```", "", raw)
    return json.loads(raw)

# ================= UI =================

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>AI Data Entry Enterprise</title>
<style>
body{font-family:Arial;background:#0f172a;color:#fff;margin:0;padding:0}
.container{max-width:1200px;margin:auto;padding:20px}
textarea{width:100%;height:160px}
button{padding:10px 20px;margin:5px;border:0;border-radius:6px;cursor:pointer}
.card{background:#111827;padding:15px;border-radius:10px;margin-top:15px}
table{width:100%;border-collapse:collapse}
td,th{border:1px solid #334155;padding:8px}
input{padding:6px}
</style>
</head>
<body>
<div class="container">
<h2>AI Data Entry Web Application (Gemini AI)</h2>

<textarea id="text"></textarea><br>
<input type="file" id="file"><br><br>

<button onclick="analyze()">Analyze</button>
<button onclick="exportExcel()">Export Excel</button>
<button onclick="clearAll()">Clear</button>

<div class="card">
<h3>Custom Field</h3>
<input id="cf_name" placeholder="Field">
<input id="cf_value" placeholder="Value">
<button onclick="addField()">Add</button>
</div>

<div class="card">
<h3>Extracted Data</h3>
<div id="result"></div>
</div>
</div>

<script>
let extracted = {}

function render(data){
 let html="<table><tr><th>Field</th><th>Value</th></tr>";
 for(let k in data){
   html+=`<tr><td>${k}</td><td>${JSON.stringify(data[k])}</td></tr>`;
 }
 html+="</table>";
 document.getElementById("result").innerHTML=html;
}

async function analyze(){
 let text=document.getElementById("text").value;
 let file=document.getElementById("file").files[0];
 let fd=new FormData();
 if(text) fd.append("text",text);
 if(file) fd.append("file",file);

 let r=await fetch("/analyze",{method:"POST",body:fd});
 let j=await r.json();
 extracted=j.data;
 render(extracted);
}

async function exportExcel(){
 let r=await fetch("/export");
 let blob=await r.blob();
 let a=document.createElement("a");
 a.href=URL.createObjectURL(blob);
 a.download="extracted.xlsx";
 a.click();
}

function clearAll(){
 extracted={}
 document.getElementById("text").value="";
 document.getElementById("file").value="";
 document.getElementById("result").innerHTML="";
}

function addField(){
 let f=document.getElementById("cf_name").value;
 let v=document.getElementById("cf_value").value;
 if(!extracted[f]) extracted[f]=[];
 extracted[f].push(v);
 render(extracted);
}
</script>
</body>
</html>
"""

# ================= API =================

@app.post("/analyze")
async def analyze(text: str = Form(None), file: UploadFile = File(None)):
    content_text = ""

    if file:
        raw = await file.read()
        extracted = extract_text_from_file(file, raw)
        if isinstance(extracted, Image.Image):
            data = gemini_image_analyze(extracted)
        else:
            content_text += extracted

    if text:
        content_text += "\n" + text

    data = gemini_analyze(content_text)
    global LAST_ANALYSIS
    LAST_ANALYSIS = data
    return {"status":"ok","data":data}

@app.get("/export")
async def export_excel():
    if not LAST_ANALYSIS:
        return JSONResponse({"error":"No data"})
    rows=[]
    for k,v in LAST_ANALYSIS.items():
        if isinstance(v,list):
            for i in v:
                rows.append({"Field":k,"Value":i})
        else:
            rows.append({"Field":k,"Value":v})
    df=pd.DataFrame(rows)
    file="export.xlsx"
    df.to_excel(file,index=False)
    return FileResponse(file,filename="extracted.xlsx")

# ================= RUN =================
# uvicorn backend.main:app --host 0.0.0.0 --port $PORT
