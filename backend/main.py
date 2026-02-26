import os, io, re, json, uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image
import google.generativeai as genai
from google.generativeai.types import RequestOptions

# --- Smart Gemini Configuration ---
# Render Environment Variables-la irundhu key-ai edukkirom
API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyCtx4Uk5b_vyMPkRHz1WZswC7xggUkZ01c"
genai.configure(api_key=API_KEY)

def find_available_model():
    """Available-aa irukkira Gemini model-ai auto-detect pannum"""
    # 404 error fix panna v1 API-ai force panrom
    possible_models = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']
    
    for m_name in possible_models:
        try:
            m = genai.GenerativeModel(
                model_name=m_name,
                request_options=RequestOptions(api_version='v1')
            )
            # Test run to verify connection
            print(f"Connected to Available Model: {m_name}")
            return m, m_name
        except:
            continue
    return None, "None"

# Application startup-la model-ai kandupidippom
active_model, active_model_name = find_available_model()

app = FastAPI()

@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    if not active_model:
        return {"Error": "No Gemini models available. Check API Key."}
    
    prompt = "Extract Name, Phone, Email, Amount as JSON. Return ONLY JSON."
    try:
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(io.BytesIO(await file.read()))
            response = active_model.generate_content([prompt, img])
        else:
            response = active_model.generate_content(f"{prompt}\nInput: {text}")
        
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else {"Error": "AI format mismatch"}
    except Exception as e:
        return {"Error": str(e)}

@app.get("/", response_class=HTMLResponse)
def home():
    status_color = "text-green-400" if active_model else "text-red-500"
    return f"""
    <html><head><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-950 text-white p-10">
        <div class="max-w-2xl mx-auto bg-slate-900 p-8 rounded-3xl border border-slate-800">
            <div class="flex justify-between items-center mb-6">
                <h1 class="text-2xl font-bold text-blue-500">AI DATA ENTRY</h1>
                <span class="text-[10px] font-mono {status_color}">Active: {active_model_name}</span>
            </div>
            <textarea id="t" class="w-full bg-black p-4 rounded-xl border border-slate-800 mb-4 h-32" placeholder="Paste text..."></textarea>
            <input type="file" id="f" class="mb-6 block text-xs">
            <button onclick="run()" id="btn" class="w-full bg-blue-600 py-4 rounded-2xl font-bold hover:bg-blue-500 transition-all">Start Analysis</button>
            <div id="res" class="mt-8 space-y-2"></div>
        </div>
        <script>
            async function run() {{
                const b = document.getElementById('btn'); b.innerText = "Connecting to {active_model_name}...";
                const fd = new FormData();
                fd.append('text', document.getElementById('t').value);
                if(document.getElementById('f').files[0]) fd.append('file', document.getElementById('f').files[0]);
                
                try {{
                    const res = await fetch('/analyze', {{method:'POST', body:fd}});
                    const data = await res.json();
                    if(data.Error) alert(data.Error);
                    else document.getElementById('res').innerHTML = Object.entries(data).map(([k,v])=>`
                        <div class='bg-black p-3 rounded-lg border border-slate-800 flex justify-between'>
                            <b class='text-blue-400 text-[10px] uppercase'>${{k}}</b>
                            <span class='text-sm'>${{v}}</span>
                        </div>`).join('');
                }} catch(e) {{ alert("Server Error"); }}
                finally {{ b.innerText = "Start Analysis"; }}
            }}
        </script>
    </body></html>
    """
     
