from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import uvicorn, io, re, json, os, pandas as pd
from PIL import Image
import pytesseract, pdfplumber, docx
from datetime import datetime
from typing import List, Dict

app = FastAPI()

# ---------------------------
# STORAGE (Memory & History)
# ---------------------------
HISTORY_FILE = "analysis_history.json"

def get_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f: return json.load(f)
    return []

def save_to_history(data):
    history = get_history()
    data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history.insert(0, data) # Put new one at top
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[:10], f, indent=4) # Keep last 10

# ---------------------------
# AI EXTRACTION LOGIC (Improved)
# ---------------------------
def ai_extract(text):
    text_clean = text.replace('\n', ' ')
    result = {
        "Name": ", ".join(re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*', text)) or "N/A",
        "Age": re.search(r'(\d{1,3})\s*(?:years|age)', text, re.I).group(1) if re.search(r'(\d{1,3})\s*(?:years|age)', text, re.I) else "N/A",
        "Gender": "Male" if "male" in text.lower() else ("Female" if "female" in text.lower() else "N/A"),
        "Phone": ", ".join(re.findall(r'\b\d{10}\b', text)) or "N/A",
        "Email": ", ".join(re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)) or "N/A",
        "City": re.search(r'City\s*([A-Za-z]+)', text, re.I).group(1) if re.search(r'City\s*([A-Za-z]+)', text, re.I) else "N/A",
        "Salary": ", ".join(re.findall(r'(?:salary|paid)\s*(?:is|amount)?\s*(\d+)', text, re.I)) or "N/A",
        "Date": ", ".join(re.findall(r'\b\d{2}/\d{2}/\d{4}\b', text)) or "N/A"
    }
    return result

@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    content = text
    if file:
        data = await file.read()
        fname = file.filename.lower()
        if fname.endswith((".png", ".jpg", ".jpeg")):
            img = Image.open(io.BytesIO(data))
            content += "\n" + pytesseract.image_to_string(img)
        elif fname.endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                content += "\n" + "".join([p.extract_text() for p in pdf.pages])
    
    extracted = ai_extract(content)
    save_to_history(extracted)
    return extracted

@app.get("/history")
async def fetch_history():
    return get_history()

@app.post("/export")
async def export(data: List[Dict]):
    df = pd.DataFrame(data)
    file_path = "extracted_data.xlsx"
    df.to_excel(file_path, index=False)
    return FileResponse(file_path, filename="Data_Export.xlsx")

# ---------------------------
# MODERN DARK UI (Tailwind)
# ---------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Data Entry - Dark Worker</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0f172a; color: #e2e8f0; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid #334155; }
        input, textarea { background: #1e293b !important; color: white !important; border: 1px solid #334155 !important; }
    </style>
</head>
<body class="p-4 md:p-8">
    <div class="max-w-4xl mx-auto space-y-6">
        <h1 class="text-2xl font-bold text-blue-400">AI Data Entry – Automated Data Worker</h1>
        
        <div class="glass p-6 rounded-xl shadow-2xl">
            <p class="mb-2 text-sm text-gray-400">📂 Upload text / notes / PDF / Image</p>
            <input type="file" id="fileInput" class="mb-4 block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700">
            <textarea id="textInput" rows="6" class="w-full p-3 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" placeholder="Enter or paste input..."></textarea>
            
            <div class="mt-4 flex gap-3">
                <button onclick="doAnalyze()" class="bg-cyan-600 hover:bg-cyan-500 px-6 py-2 rounded-md font-medium transition">Analyze</button>
                <button onclick="clearAll()" class="bg-gray-700 hover:bg-gray-600 px-6 py-2 rounded-md font-medium transition">Clear</button>
                <button onclick="exportToExcel()" class="bg-indigo-600 hover:bg-indigo-500 px-6 py-2 rounded-md font-medium transition">Export Excel</button>
            </div>
        </div>

        <div class="glass p-6 rounded-xl overflow-hidden">
            <h2 class="text-lg font-semibold mb-4 border-b border-gray-700 pb-2">Extracted Data:</h2>
            <table class="w-full text-left">
                <thead><tr class="text-gray-400 border-b border-gray-800"><th class="py-2">Field</th><th>Values</th></tr></thead>
                <tbody id="dataTable">
                    </tbody>
            </table>

            <div class="mt-8 border-t border-gray-800 pt-4">
                <h3 class="text-sm font-bold text-gray-400 mb-3">+ Custom Fields</h3>
                <div class="flex gap-2">
                    <input type="text" id="custField" placeholder="Field name" class="p-2 rounded w-1/3 text-sm">
                    <input type="text" id="custVal" placeholder="Value" class="p-2 rounded w-1/2 text-sm">
                    <button onclick="addCustomRow()" class="bg-emerald-600 px-4 py-2 rounded text-sm">Add</button>
                </div>
            </div>
        </div>

        <div class="glass p-6 rounded-xl">
            <h2 class="text-lg font-semibold mb-4 text-blue-300">🕒 Last 10 Analysis</h2>
            <div id="historyList" class="space-y-2 text-xs text-gray-400"></div>
        </div>
    </div>

    <script>
        let currentData = {};

        async function doAnalyze() {
            const fd = new FormData();
            const file = document.getElementById('fileInput').files[0];
            const text = document.getElementById('textInput').value;
            if(file) fd.append('file', file);
            fd.append('text', text);

            const res = await fetch('/analyze', {method:'POST', body:fd});
            currentData = await res.json();
            renderTable();
            loadHistory();
        }

        function renderTable() {
            const tbody = document.getElementById('dataTable');
            tbody.innerHTML = Object.entries(currentData).map(([k,v]) => 
                `<tr class="border-b border-gray-800"><td class="py-3 font-medium text-blue-200">${k}</td><td class="text-gray-300">${v}</td></tr>`
            ).join('');
        }

        function addCustomRow() {
            const k = document.getElementById('custField').value;
            const v = document.getElementById('custVal').value;
            if(k && v) {
                currentData[k] = v;
                renderTable();
                document.getElementById('custField').value = '';
                document.getElementById('custVal').value = '';
            }
        }

        async function loadHistory() {
            const res = await fetch('/history');
            const data = await res.json();
            document.getElementById('historyList').innerHTML = data.map(h => 
                `<div class="p-2 bg-slate-800 rounded flex justify-between"><span>${h.Name} (${h.timestamp})</span><span class="text-blue-500 cursor-pointer" onclick='viewHistoryItem(${JSON.stringify(h)})'>View</span></div>`
            ).join('');
        }

        function viewHistoryItem(item) {
            currentData = item;
            renderTable();
        }

        async function exportToExcel() {
            const res = await fetch('/export', {
                method: 'POST', 
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify([currentData])
            });
            const blob = await res.blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = "Extracted_Data.xlsx";
            a.click();
        }

        function clearAll() {
            document.getElementById('textInput').value = '';
            document.getElementById('dataTable').innerHTML = '';
            currentData = {};
        }

        window.onload = loadHistory;
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
        
