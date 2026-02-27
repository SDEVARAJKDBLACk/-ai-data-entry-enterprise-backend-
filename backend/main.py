import os
import json
import re
import google.generativeai as genai
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# --- 1. API CONFIGURATION ---
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    # Latest stable configuration to avoid 404
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. FRONTEND (HTML/JS) ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Data Entry - Automated Data Worker</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); }
        .success-glow { box-shadow: 0 0 15px rgba(34, 197, 94, 0.5); }
    </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen font-sans">
    <div class="container mx-auto px-4 py-10">
        <header class="text-center mb-10">
            <h1 class="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">
                AI Data Entry - Automated Data Worker
            </h1>
            <p class="text-slate-400 mt-2">Paste raw text and let the AI fill the database for you.</p>
        </header>

        <div class="grid lg:grid-cols-2 gap-8 max-w-6xl mx-auto">
            
            <div class="glass p-6 rounded-2xl border border-slate-700">
                <h2 class="text-xl font-semibold mb-4 flex items-center gap-2 text-blue-400">
                    <span>⚡</span> Raw Data Input
                </h2>
                <textarea id="rawInput" placeholder="Paste data here... (e.g., Ramesh from Chennai, age 28, working as an Engineer)" 
                    class="w-full h-48 bg-slate-800 border border-slate-600 rounded-xl p-4 text-sm focus:ring-2 focus:ring-blue-500 outline-none transition"></textarea>
                <button onclick="processData()" id="processBtn"
                    class="w-full mt-4 bg-blue-600 hover:bg-blue-700 py-3 rounded-xl font-bold transition flex justify-center items-center gap-2">
                    Start Automation
                </button>
            </div>

            <div class="glass p-6 rounded-2xl border border-slate-700">
                <h2 class="text-xl font-semibold mb-4 flex items-center gap-2 text-emerald-400">
                    <span>📋</span> Automated Output
                </h2>
                <div id="status" class="hidden mb-4 p-2 text-center text-xs bg-emerald-500/20 text-emerald-400 rounded-lg">
                    Data Extracted Successfully!
                </div>
                <form id="dataForm" class="space-y-4">
                    <div>
                        <label class="text-xs text-slate-400 uppercase tracking-widest">Full Name</label>
                        <input type="text" id="name" class="w-full bg-slate-800/50 border border-slate-600 rounded-lg p-3">
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="text-xs text-slate-400 uppercase tracking-widest">Age</label>
                            <input type="text" id="age" class="w-full bg-slate-800/50 border border-slate-600 rounded-lg p-3">
                        </div>
                        <div>
                            <label class="text-xs text-slate-400 uppercase tracking-widest">Location</label>
                            <input type="text" id="location" class="w-full bg-slate-800/50 border border-slate-600 rounded-lg p-3">
                        </div>
                    </div>
                    <div>
                        <label class="text-xs text-slate-400 uppercase tracking-widest">Job Role</label>
                        <input type="text" id="job" class="w-full bg-slate-800/50 border border-slate-600 rounded-lg p-3">
                    </div>
                </form>
            </div>

        </div>
    </div>

    <script>
        async function processData() {
            const btn = document.getElementById('processBtn');
            const rawText = document.getElementById('rawInput').value;
            if(!rawText) return alert("Please paste some text first!");

            btn.disabled = true;
            btn.innerText = "Extracting...";

            try {
                const formData = new FormData();
                formData.append('text', rawText);

                const response = await fetch('/automate', { method: 'POST', body: formData });
                const result = await response.json();

                if(result.success) {
                    document.getElementById('name').value = result.data.name || '';
                    document.getElementById('age').value = result.data.age || '';
                    document.getElementById('location').value = result.data.location || '';
                    document.getElementById('job').value = result.data.job || '';
                    
                    document.getElementById('status').classList.remove('hidden');
                    setTimeout(() => document.getElementById('status').classList.add('hidden'), 3000);
                }
            } catch (err) {
                alert("Automation failed. Check logs.");
            } finally {
                btn.disabled = false;
                btn.innerText = "Start Automation";
            }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_CONTENT

@app.post("/automate")
async def automate_worker(text: str = Form(...)):
    if not model:
        return {"success": False, "error": "AI Config Missing"}
    
    # Precise prompt for Data Worker
    prompt = (
        f"Extract information from the text: '{text}'. "
        "Return ONLY a JSON object with keys: name, age, location, job. "
        "If a value is missing, use an empty string. "
    )

    try:
        response = model.generate_content(prompt)
        # Cleaning the AI response to get valid JSON
        json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        extracted_data = json.loads(json_str)
        return {"success": True, "data": extracted_data}
    except Exception as e:
        return {"success": False, "error": str(e)}
