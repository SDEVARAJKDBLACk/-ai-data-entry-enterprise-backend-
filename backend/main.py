import os
import json
import requests
import re
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

app = FastAPI()

# 1. API KEY SETUP
API_KEY = os.getenv("GEMINI_API_KEY")

# 2. STABLE V1 URL (v1beta mothamaa thookiyaachu)
# Idhu dhaan direct stable production endpoint
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>AI Data Entry - Automated Data Worker</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-white p-6 md:p-12 font-sans">
        <div class="max-w-3xl mx-auto">
            <header class="text-center mb-10">
                <h1 class="text-4xl font-black text-blue-500 tracking-tight">AI DATA ENTRY</h1>
                <p class="text-slate-400 uppercase text-xs tracking-[0.2em] mt-2 font-bold">Automated Data Worker v1.0 (Stable)</p>
            </header>
            
            <div class="bg-slate-800 border border-slate-700 p-6 rounded-3xl shadow-2xl">
                <label class="block text-sm font-bold text-slate-400 mb-2 uppercase tracking-wide">Paste Raw Data</label>
                <textarea id="rawInput" class="w-full h-40 bg-slate-900 border border-slate-700 p-4 rounded-2xl mb-4 focus:ring-2 focus:ring-blue-500 outline-none text-slate-200" 
                placeholder="Example: Senthil, 34 years old, lives in Madurai, works as a Driver..."></textarea>
                
                <button onclick="processData()" id="btn" class="w-full bg-blue-600 hover:bg-blue-700 py-4 rounded-2xl font-black text-lg transition-all transform active:scale-95 shadow-lg shadow-blue-900/20">
                    EXTRACT DATA
                </button>
            </div>

            <div id="loader" class="hidden mt-6 text-center text-blue-400 font-bold animate-pulse">
                ⚙️ SYSTEM ANALYZING DATA...
            </div>

            <div class="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="bg-slate-800/50 p-4 rounded-2xl border border-slate-700">
                    <label class="text-[10px] text-slate-500 font-black uppercase">Full Name</label>
                    <input id="name" class="w-full bg-transparent p-1 text-blue-400 font-bold text-lg outline-none" readonly>
                </div>
                <div class="bg-slate-800/50 p-4 rounded-2xl border border-slate-700">
                    <label class="text-[10px] text-slate-500 font-black uppercase">Age</label>
                    <input id="age" class="w-full bg-transparent p-1 text-blue-400 font-bold text-lg outline-none" readonly>
                </div>
                <div class="bg-slate-800/50 p-4 rounded-2xl border border-slate-700">
                    <label class="text-[10px] text-slate-500 font-black uppercase">Location</label>
                    <input id="loc" class="w-full bg-transparent p-1 text-blue-400 font-bold text-lg outline-none" readonly>
                </div>
                <div class="bg-slate-800/50 p-4 rounded-2xl border border-slate-700">
                    <label class="text-[10px] text-slate-500 font-black uppercase">Occupation</label>
                    <input id="job" class="w-full bg-transparent p-1 text-blue-400 font-bold text-lg outline-none" readonly>
                </div>
            </div>
        </div>

        <script>
            async function processData() {
                const btn = document.getElementById('btn');
                const loader = document.getElementById('loader');
                const text = document.getElementById('rawInput').value;
                if(!text) return;

                btn.disabled = true; btn.innerText = "WORKING...";
                loader.classList.remove('hidden');

                const fd = new FormData();
                fd.append('data', text);

                try {
                    const response = await fetch('/extract', { method: 'POST', body: fd });
                    const result = await response.json();

                    if(result.success) {
                        document.getElementById('name').value = result.info.name || '-';
                        document.getElementById('age').value = result.info.age || '-';
                        document.getElementById('loc').value = result.info.location || '-';
                        document.getElementById('job').value = result.info.job || '-';
                    } else {
                        alert("ERROR: " + result.error);
                    }
                } catch(e) {
                    alert("CONNECTION FAILED");
                } finally {
                    btn.disabled = false; btn.innerText = "EXTRACT DATA";
                    loader.classList.add('hidden');
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/extract")
async def extract(data: str = Form(...)):
    # AI response-ai JSON-aa mattum thara solli strict prompt
    prompt = f"Extract Name, Age, Location, and Job from: '{data}'. Return ONLY JSON format: {{'name': '', 'age': '', 'location': '', 'job': ''}}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        # Direct Stable v1 Request
        resp = requests.post(GEMINI_URL, json=payload, timeout=15)
        resp_json = resp.json()

        if resp.status_code != 200:
            return {"success": False, "error": f"Status {resp.status_code}: Check API Key."}

        ai_text = resp_json['candidates'][0]['content']['parts'][0]['text']
        
        # Regex to filter JSON from AI text
        match = re.search(r'\{.*\}', ai_text, re.DOTALL)
        if match:
            extracted_json = json.loads(match.group().replace("'", '"'))
            return {"success": True, "info": extracted_json}
        
        return {"success": False, "error": "AI could not structure data."}
    except Exception as e:
        return {"success": False, "error": "Server busy. Try again."}
    
