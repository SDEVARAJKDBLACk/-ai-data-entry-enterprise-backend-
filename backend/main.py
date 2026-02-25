import os, io, re, json, uvicorn, pandas as pd
from datetime import datetime
from typing import List, Dict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image
import pdfplumber, docx
import google.generativeai as genai

# --- Config & AI ---
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI()

# --- Files for Persistence ---
USERS_FILE = "users.json"
HISTORY_FILE = "history.json"
MEMORY_FILE = "field_memory.json" # Auto-learning memory

def load_db(file):
    if os.path.exists(file):
        with open(file, "r") as f: return json.load(f)
    return [] if "history" in file else {}

def save_db(file, data):
    with open(file, "w") as f: json.dump(data, f, indent=4)

# --- AI Extraction Logic ---
async def extract_data(content, is_image=False, image_data=None):
    # Load memory to tell AI which custom fields to look for
    memory = load_db(MEMORY_FILE)
    custom_fields = ", ".join(memory.keys()) if memory else "None"

    prompt = f"""
    Analyze the text and extract data in JSON format.
    Standard Fields: Name, Reference Name, Age, Gender, Phone, Email, Address, City, State, Country, Pincode, Company, Job Title, Location, Product Name, Quantity, Price, Salary, Total Amount, Date, Transaction Number.
    Custom Fields to detect: {custom_fields}
    
    Instructions:
    1. For multi-value fields (like multiple names or phones), use a comma-separated string.
    2. If any field is missing, use "N/A".
    3. Be precise with human names vs company names.
    """
    
    if is_image:
        response = model.generate_content([prompt, image_data])
    else:
        response = model.generate_content(f"{prompt} \nText: {content}")
    
    json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
    return json.loads(json_match.group()) if json_match else {"Error": "AI Error"}

# --- Routes ---
@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    if not text and not file: raise HTTPException(status_code=400)
    
    content = text
    extracted = {}
    if file:
        f_bytes = await file.read()
        f_name = file.filename.lower()
        if f_name.endswith(('.png', '.jpg', '.jpeg')):
            extracted = await extract_data("", is_image=True, image_data=Image.open(io.BytesIO(f_bytes)))
        else:
            if f_name.endswith('.pdf'):
                with pdfplumber.open(io.BytesIO(f_bytes)) as pdf: content += "\n" + "".join([p.extract_text() for p in pdf.pages])
            elif f_name.endswith('.docx'):
                doc = docx.Document(io.BytesIO(f_bytes))
                content += "\n" + "\n".join([p.text for p in doc.paragraphs])
            extracted = await extract_data(content)
    else:
        extracted = await extract_data(content)

    # Save to History
    history = load_db(HISTORY_FILE)
    extracted['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history.insert(0, extracted)
    save_db(HISTORY_FILE, history[:10])
    return extracted

@app.post("/learn") # AI Learning Route
async def learn_field(data: dict):
    memory = load_db(MEMORY_FILE)
    memory[data['field']] = True # Register new field for AI to remember
    save_db(MEMORY_FILE, memory)
    return {"status": "learned"}

@app.get("/history")
async def get_history(): return load_db(HISTORY_FILE)

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Master Worker</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background: #0b0f1a; color: #e2e8f0; }
            .glass { background: rgba(23, 32, 53, 0.8); backdrop-filter: blur(12px); border: 1px solid #2d3748; }
            .loader { border: 3px solid #1a202c; border-top: 3px solid #3b82f6; border-radius: 50%; width: 22px; height: 22px; animation: spin 1s linear infinite; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body class="p-6">
        <div class="max-w-6xl mx-auto space-y-6">
            <div class="flex justify-between items-center">
                <h1 class="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">AI DATA WORKER PRO</h1>
                <button onclick="location.reload()" class="bg-slate-800 px-4 py-2 rounded-lg text-sm border border-slate-700">Logout</button>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div class="lg:col-span-2 space-y-6">
                    <div class="glass p-6 rounded-3xl shadow-2xl">
                        <textarea id="textIn" rows="10" class="w-full bg-slate-950 p-4 rounded-2xl border border-slate-800 outline-none focus:border-blue-500 transition-all" placeholder="Paste text, notes, or messages here..."></textarea>
                        <div class="flex flex-wrap gap-4 mt-4 items-center">
                            <input type="file" id="fileIn" class="text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:bg-blue-600 file:text-white">
                            <button onclick="process()" id="anBtn" class="bg-blue-600 hover:bg-blue-500 px-10 py-3 rounded-2xl font-bold flex items-center gap-3 transition-all">
                                <span id="btnText">Analyze</span>
                                <div id="btnLoad" class="loader hidden"></div>
                            </button>
                            <button onclick="clearAll()" class="bg-slate-700 hover:bg-slate-600 px-6 py-3 rounded-2xl font-bold transition-all">Clear</button>
                        </div>
                    </div>

                    <div class="glass p-6 rounded-3xl">
                        <div class="flex justify-between items-center mb-4">
                            <h3 class="font-bold text-blue-400">Extracted Results</h3>
                            <button onclick="exportExcel()" class="bg-emerald-600 hover:bg-emerald-500 px-4 py-1.5 rounded-lg text-xs font-bold">Export Excel</button>
                        </div>
                        <div id="resTable" class="grid grid-cols-1 md:grid-cols-2 gap-4"></div>
                        
                        <div class="mt-8 pt-6 border-t border-slate-800">
                            <p class="text-xs font-bold text-slate-500 mb-3 text-uppercase uppercase tracking-widest">Add Custom Field (AI Learning)</p>
                            <div class="flex gap-2">
                                <input type="text" id="custField" placeholder="New Field Name (e.g. GST Number)" class="bg-slate-900 border border-slate-800 p-2 rounded-lg flex-1 text-sm">
                                <input type="text" id="custVal" placeholder="Value" class="bg-slate-900 border border-slate-800 p-2 rounded-lg flex-1 text-sm">
                                <button onclick="addCustom()" class="bg-indigo-600 px-4 py-2 rounded-lg text-sm font-bold">Add & Learn</button>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="glass p-6 rounded-3xl h-fit">
                    <h3 class="font-bold text-cyan-400 mb-4 flex items-center gap-2">🕒 Last Analysis History</h3>
                    <div id="histList" class="space-y-3 max-h-[600px] overflow-y-auto pr-2"></div>
                </div>
            </div>
        </div>

        <script>
            let currentData = {};

            async function process() {
                const text = document.getElementById('textIn').value;
                const file = document.getElementById('fileIn').files[0];
                if(!text && !file) return alert("Empty input!");

                const btn = document.getElementById('anBtn');
                const load = document.getElementById('btnLoad');
                btn.disabled = true;
                load.classList.remove('hidden');
                document.getElementById('btnText').innerText = "Analyzing...";

                const fd = new FormData();
                fd.append('text', text);
                if(file) fd.append('file', file);

                setTimeout(async () => {
                    try {
                        const res = await fetch('/analyze', { method: 'POST', body: fd });
                        currentData = await res.json();
                        renderTable();
                        loadHistory();
                    } catch(e) { alert("Error analyzing!"); }
                    
                    btn.disabled = false;
                    load.classList.add('hidden');
                    document.getElementById('btnText').innerText = "Analyze";
                }, 3000);
            }

            function renderTable() {
                const container = document.getElementById('resTable');
                container.innerHTML = Object.entries(currentData).map(([k,v]) => {
                    if(k==='timestamp') return '';
                    return `<div class="bg-slate-900/50 p-3 rounded-xl border border-slate-800">
                                <div class="text-[10px] text-slate-500 font-bold uppercase">${k}</div>
                                <div class="text-blue-200 font-medium">${v}</div>
                            </div>`;
                }).join('');
            }

            async function addCustom() {
                const field = document.getElementById('custField').value;
                const val = document.getElementById('custVal').value;
                if(!field || !val) return;

                currentData[field] = val;
                renderTable();

                // Tell AI to learn this field for future
                await fetch('/learn', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ field })
                });
                
                document.getElementById('custField').value = '';
                document.getElementById('custVal').value = '';
            }

            async function loadHistory() {
                const res = await fetch('/history');
                const data = await res.json();
                document.getElementById('histList').innerHTML = data.map(h => `
                    <div class="bg-slate-900 p-3 rounded-xl border border-slate-800 hover:border-blue-500 cursor-pointer transition-all" onclick='viewHist(${JSON.stringify(h)})'>
                        <div class="flex justify-between text-[10px] mb-1">
                            <span class="text-blue-400 font-bold">${h.Name || 'Unknown'}</span>
                            <span class="text-slate-600">${h.timestamp}</span>
                        </div>
                        <div class="text-[11px] text-slate-400 truncate">${h.Job_Title || h.City || 'Analysis Record'}</div>
                    </div>
                `).join('');
            }

            function viewHist(data) {
                currentData = data;
                renderTable();
            }

            function clearAll() {
                document.getElementById('textIn').value = '';
                document.getElementById('fileIn').value = '';
                document.getElementById('resTable').innerHTML = '';
                currentData = {};
            }

            function exportExcel() {
                if(Object.keys(currentData).length === 0) return alert("No data!");
                // Simulating excel export for frontend demo
                let csv = "Field,Value\\n" + Object.entries(currentData).map(e => `"${e[0]}","${e[1]}"`).join("\\n");
                let blob = new Blob([csv], {type: 'text/csv'});
                let a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = "Extracted_Data.csv";
                a.click();
            }

            window.onload = loadHistory;
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
