import os, io, re, json, uvicorn, pandas as pd
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from PIL import Image
import pdfplumber, docx
import google.generativeai as genai

# --- Config & AI ---
# Render Environment-la GEMINI_API_KEY sariya irukanum
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    # Screenshot-la ulla working key-ai backup-ah vachukalam
    API_KEY = "AIzaSyCtx4Uk5b_vyMPkRHz1WZswC7xggUkZ01c"

genai.configure(api_key=API_KEY)

# 'gemini-1.5-flash-latest' nu kudutha dhaan 404 error varadhu
model = genai.GenerativeModel('gemini-1.5-flash-latest')

app = FastAPI()

# --- Memory Handling (Render-la file save panna mudiyathu) ---
field_memory = [] # Custom fields-ai inga store pannuvom
history_data = [] # History-ai RAM-la vachukuvom

# --- AI Extraction Logic ---
async def extract_data(content, is_image=False, image_data=None):
    # Dynamic field inclusion
    base_fields = "Name, Age, Phone, Email, Company, Job Title, Amount, Date"
    custom_str = ", ".join(field_memory)
    all_fields = f"{base_fields}, {custom_str}" if field_memory else base_fields
    
    prompt = f"""
    Extract data from the text in JSON format. 
    Fields: {all_fields}
    Rules: Return ONLY a valid JSON object. If missing, use 'N/A'.
    """
    
    try:
        if is_image:
            response = model.generate_content([prompt, image_data])
        else:
            response = model.generate_content(f"{prompt} \nText: {content}")
        
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"Error": "AI response format mismatch"}
    except Exception as e:
        return {"Error": str(e)}

# --- Routes ---
@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    try:
        content = text
        extracted = {}
        
        if file:
            f_bytes = await file.read()
            f_name = file.filename.lower()
            if f_name.endswith(('.png', '.jpg', '.jpeg')):
                img = Image.open(io.BytesIO(f_bytes))
                extracted = await extract_data("", is_image=True, image_data=img)
            else:
                if f_name.endswith('.pdf'):
                    with pdfplumber.open(io.BytesIO(f_bytes)) as pdf:
                        content += "\n" + "".join([p.extract_text() or "" for p in pdf.pages])
                elif f_name.endswith('.docx'):
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
    field = data.get("field")
    if field and field not in field_memory:
        field_memory.append(field)
    return {"status": "success"}

@app.get("/export_excel")
async def export_excel():
    if not history_data:
        raise HTTPException(status_code=400, detail="No data to export")
    
    df = pd.DataFrame(history_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=data_export.xlsx"}
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
            .loader { border: 3px solid #1a202c; border-top: 3px solid #3b82f6; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body class="p-8">
        <div class="max-w-6xl mx-auto">
            <div class="flex justify-between items-center mb-10">
                <h1 class="text-3xl font-bold text-blue-400">AI DATA PRO</h1>
                <button onclick="window.location.href='/export_excel'" class="bg-green-600 px-6 py-2 rounded-xl font-bold hover:bg-green-500">Export Excel</button>
            </div>
            
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div class="lg:col-span-2 space-y-6">
                    <div class="glass p-6 rounded-3xl">
                        <input type="file" id="fileIn" class="mb-4 text-sm text-slate-400">
                        <textarea id="textIn" rows="6" class="w-full bg-slate-950 p-4 rounded-2xl border border-slate-800 focus:border-blue-500 outline-none" placeholder="Paste data here..."></textarea>
                        <button onclick="run()" id="anBtn" class="mt-4 bg-blue-600 px-10 py-3 rounded-xl font-bold flex gap-2">
                            <span id="btnTxt">Analyze Data</span>
                            <div id="btnL" class="loader hidden"></div>
                        </button>
                    </div>
                    <div id="resTable" class="glass p-6 rounded-3xl grid grid-cols-2 gap-4"></div>
                </div>

                <div class="space-y-6">
                    <div class="glass p-6 rounded-3xl">
                        <h3 class="text-cyan-400 font-bold mb-4">Add Custom Field</h3>
                        <input type="text" id="newF" class="w-full bg-slate-900 p-2 rounded mb-2 border border-slate-700" placeholder="e.g. GST Number">
                        <button onclick="addField()" class="w-full bg-indigo-600 py-2 rounded font-bold">Register Field</button>
                    </div>
                    <div id="histList" class="glass p-6 rounded-3xl space-y-2 h-96 overflow-y-auto"></div>
                </div>
            </div>
        </div>
        <script>
            async function run() {
                const btn = document.getElementById('anBtn');
                const load = document.getElementById('btnL');
                btn.disabled = true; load.classList.remove('hidden');
                
                const fd = new FormData();
                fd.append('text', document.getElementById('textIn').value);
                const file = document.getElementById('fileIn').files[0];
                if(file) fd.append('file', file);

                try {
                    const res = await fetch('/analyze', { method: 'POST', body: fd });
                    const data = await res.json();
                    if(data.Error) alert("Error: " + data.Error);
                    else {
                        document.getElementById('resTable').innerHTML = Object.entries(data).map(([k,v]) => 
                            k !== 'timestamp' ? `<div class='bg-slate-900 p-3 rounded-xl border border-slate-800'><b class='text-slate-500'>${k}</b><br>${v}</div>` : ''
                        ).join('');
                        loadHistory();
                    }
                } catch(e) { alert("Server Error!"); }
                finally { btn.disabled = false; load.classList.add('hidden'); }
            }

            async function addField() {
                const field = document.getElementById('newF').value;
                if(!field) return;
                await fetch('/add_field', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({field})
                });
                alert("AI Learned: " + field);
                document.getElementById('newF').value = '';
            }

            async function loadHistory() {
                const res = await fetch('/history');
                const data = await res.json();
                document.getElementById('histList').innerHTML = data.map(h => `
                    <div class='bg-slate-900 p-3 rounded-xl border border-slate-800 text-xs'>
                        <b class='text-blue-400'>${h.Name || 'New Record'}</b><br><span class='text-slate-600'>${h.timestamp}</span>
                    </div>`).join('');
            }
            window.onload = loadHistory;
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
