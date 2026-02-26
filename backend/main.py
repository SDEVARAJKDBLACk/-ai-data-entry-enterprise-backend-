import os, io, re, json, uvicorn, pandas as pd
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from PIL import Image
import pdfplumber, docx
import google.generativeai as genai

# --- Config & AI ---
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    API_KEY = "AIzaSyCtx4Uk5b_vyMPkRHz1WZswC7xggUkZ01c" # Backup Key

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

app = FastAPI()

# --- Memory Data (No JSON Files for Render) ---
field_memory = [] # Custom fields list
history_data = [] # Analysis history

# --- AI Extraction Logic ---
async def extract_data(content, is_image=False, image_data=None):
    # Dynamic fields selection
    base_fields = "Name, Age, Phone, Email, Company, Job Title, Amount, Date"
    custom_str = ", ".join(field_memory)
    all_fields = f"{base_fields}, {custom_str}" if field_memory else base_fields
    
    prompt = f"Extract these fields as JSON: {all_fields}. If missing, use 'N/A'. Return ONLY JSON."
    
    try:
        response = model.generate_content([prompt, image_data]) if is_image else model.generate_content(f"{prompt}\nText: {content}")
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else {"Error": "AI Format Error"}
    except Exception as e:
        return {"Error": str(e)}

# --- Routes ---
@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    try:
        content = text
        if file:
            f_bytes = await file.read()
            if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                extracted = await extract_data("", True, Image.open(io.BytesIO(f_bytes)))
            else:
                if file.filename.endswith('.pdf'):
                    with pdfplumber.open(io.BytesIO(f_bytes)) as pdf:
                        content += "\n" + "".join([p.extract_text() or "" for p in pdf.pages])
                elif file.filename.endswith('.docx'):
                    doc = docx.Document(io.BytesIO(f_bytes))
                    content += "\n" + "\n".join([p.text for p in doc.paragraphs])
                extracted = await extract_data(content)
        else:
            extracted = await extract_data(content)

        if "Error" not in extracted:
            extracted['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            history_data.insert(0, extracted)
        return extracted
    except Exception as e:
        return JSONResponse({"Error": str(e)}, status_code=500)

@app.post("/add_field")
async def add_field(data: dict):
    new_field = data.get("field")
    if new_field and new_field not in field_memory:
        field_memory.append(new_field)
    return {"status": "success", "fields": field_memory}

@app.get("/export_excel")
async def export_excel():
    if not history_data:
        raise HTTPException(status_code=400, detail="No data to export")
    
    df = pd.DataFrame(history_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='ExtractedData')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=extracted_data.xlsx"}
    )

@app.get("/history")
async def get_history():
    return history_data[:10]

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>AI Data Pro</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background: #0b0f1a; color: #f1f5f9; }
            .glass { background: rgba(23, 32, 53, 0.9); border: 1px solid #2d3748; }
        </style>
    </head>
    <body class="p-8">
        <div class="max-w-6xl mx-auto">
            <div class="flex justify-between items-center mb-6">
                <h1 class="text-2xl font-bold text-blue-400">AI DATA WORKER PRO</h1>
                <button onclick="window.location.href='/export_excel'" class="bg-green-600 px-4 py-2 rounded-lg font-bold">Export Excel</button>
            </div>
            
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div class="lg:col-span-2 space-y-6">
                    <div class="glass p-6 rounded-3xl">
                        <textarea id="textIn" rows="6" class="w-full bg-slate-950 p-4 rounded-xl mb-4" placeholder="Paste data..."></textarea>
                        <button onclick="run()" id="anBtn" class="bg-blue-600 px-8 py-3 rounded-xl font-bold">Analyze</button>
                    </div>
                    
                    <div class="glass p-6 rounded-3xl">
                        <h3 class="text-blue-300 font-bold mb-4">Results</h3>
                        <div id="resTable" class="grid grid-cols-2 gap-4"></div>
                    </div>
                </div>

                <div class="space-y-6">
                    <div class="glass p-6 rounded-3xl">
                        <h3 class="text-cyan-400 font-bold mb-4">Add Custom Field</h3>
                        <input type="text" id="newField" class="w-full bg-slate-900 p-2 rounded mb-2" placeholder="Ex: GST Number">
                        <button onclick="addField()" class="w-full bg-indigo-600 py-2 rounded font-bold">Add Field</button>
                    </div>
                    <div id="histList" class="glass p-6 rounded-3xl space-y-2"></div>
                </div>
            </div>
        </div>
        <script>
            async function run() {
                const btn = document.getElementById('anBtn');
                btn.innerText = "Analyzing..."; btn.disabled = true;
                const fd = new FormData();
                fd.append('text', document.getElementById('textIn').value);
                
                const res = await fetch('/analyze', { method: 'POST', body: fd });
                const data = await res.json();
                
                if(data.Error) alert(data.Error);
                else {
                    document.getElementById('resTable').innerHTML = Object.entries(data).map(([k,v]) => 
                        k!=='timestamp' ? `<div class='bg-slate-900 p-2 rounded'><b>${k}:</b> ${v}</div>` : ''
                    ).join('');
                }
                btn.innerText = "Analyze"; btn.disabled = false;
                loadHistory();
            }

            async function addField() {
                const f = document.getElementById('newField').value;
                if(!f) return;
                await fetch('/add_field', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({field: f})
                });
                alert("Field Added: " + f);
                document.getElementById('newField').value = '';
            }

            async function loadHistory() {
                const res = await fetch('/history');
                const data = await res.json();
                document.getElementById('histList').innerHTML = data.map(h => `<div class='text-xs p-2 border-b border-slate-800'>${h.Name || 'Record'} - ${h.timestamp}</div>`).join('');
            }
            window.onload = loadHistory;
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
        
