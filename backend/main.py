import os
import requests
import json
import re
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse

app = FastAPI()
API_KEY = os.getenv("GEMINI_API_KEY")

# Indha URL dhaan Gemini 1.5 Flash (v1 Stable)-oda best endpoint
URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def home(request: Request):
    if request.method == "HEAD": return HTMLResponse(content="", status_code=200)
    return """
    <html lang="en">
    <head>
        <title>AI Data Extractor</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-white font-sans p-10">
        <div class="max-w-2xl mx-auto">
            <h1 class="text-3xl font-bold text-center text-blue-400 mb-8">Data Extraction Pro</h1>
            <div class="bg-gray-800 p-6 rounded-2xl shadow-xl border border-gray-700">
                <textarea id="dataInput" class="w-full bg-gray-900 p-4 rounded-xl mb-4 border border-gray-600 outline-none focus:border-blue-500 h-32" placeholder="Paste raw text here..."></textarea>
                <button onclick="extract()" id="btn" class="w-full bg-blue-600 hover:bg-blue-700 p-4 rounded-xl font-bold transition">Extract with Gemini 1.5 Flash</button>
            </div>
            
            <div id="loader" class="hidden mt-6 text-center text-blue-300 animate-pulse font-semibold italic">Processing with AI...</div>

            <div class="mt-8 grid grid-cols-2 gap-4">
                <div class="bg-gray-800 p-4 rounded-xl border border-gray-700">
                    <label class="text-xs text-gray-500 font-bold uppercase">Name</label>
                    <div id="outName" class="text-xl text-blue-300 font-semibold">-</div>
                </div>
                <div class="bg-gray-800 p-4 rounded-xl border border-gray-700">
                    <label class="text-xs text-gray-500 font-bold uppercase">Age</label>
                    <div id="outAge" class="text-xl text-blue-300 font-semibold">-</div>
                </div>
            </div>
        </div>
        <script>
            async function extract() {
                const btn = document.getElementById('btn');
                const loader = document.getElementById('loader');
                const text = document.getElementById('dataInput').value;
                if(!text) return alert("Text podunga boss!");

                btn.disabled = true; loader.classList.remove('hidden');
                const fd = new FormData(); fd.append('data', text);

                try {
                    const res = await fetch('/extract', { method: 'POST', body: fd });
                    const d = await res.json();
                    if(d.success) {
                        document.getElementById('outName').innerText = d.info.name || 'Not found';
                        document.getElementById('outAge').innerText = d.info.age || 'Not found';
                    } else { alert("AI Error: " + d.error); }
                } catch(e) { alert("Connection Error!"); }
                finally { btn.disabled = false; loader.classList.add('hidden'); }
            }
        </script>
    </body>
    </html>
    """

@app.post("/extract")
async def extract(data: str = Form(...)):
    # Instruction model-ukku clear-aa JSON-la kettu vaanguraen
    prompt = f"Extract 'name' and 'age' from the following text and return ONLY a valid JSON object: '{data}'"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        resp = requests.post(URL, json=payload, timeout=10)
        res_j = resp.json()
        if resp.status_code != 200:
            return {"success": False, "error": res_j.get('error', {}).get('message', 'API Error')}
        
        # AI tharura text-la irundhu JSON-ai edukkiraen
        ai_text = res_j['candidates'][0]['content']['parts'][0]['text']
        match = re.search(r'\{.*\}', ai_text, re.DOTALL)
        if match:
            return {"success": True, "info": json.loads(match.group())}
        return {"success": False, "error": "AI response error"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    
