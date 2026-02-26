import os, io, re, json, uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image
import google.generativeai as genai

# --- Gemini API Connection Fix ---
API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyCtx4Uk5b_vyMPkRHz1WZswC7xggUkZ01c"
genai.configure(api_key=API_KEY)

def initialize_gemini():
    """Available models-ai list panni sariyana model-ai select pannum"""
    try:
        # 404 error fix: 'models/' prefix illama try panrom
        # Most stable name for many regions
        model_name = 'gemini-1.5-flash' 
        return genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"Primary model failed: {e}")
        return genai.GenerativeModel('gemini-pro') # Emergency Fallback

model = initialize_gemini()
app = FastAPI()

# --- AI Extraction Logic ---
async def extract_data(content, is_image=False, image_data=None):
    prompt = "Extract Name, Phone, Email, Company, Amount as JSON. Return ONLY JSON. Use 'N/A' if missing."
    try:
        if is_image:
            response = model.generate_content([prompt, image_data])
        else:
            response = model.generate_content(f"{prompt}\nInput: {content}")
        
        # Cleaning AI text response
        clean_json = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(clean_json.group()) if clean_json else {"Error": "AI Format Mismatch"}
    except Exception as e:
        # Error analysis fix
        return {"Error": f"Gemini Error: {str(e)}"}

# --- Routes ---
@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    try:
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(io.BytesIO(await file.read()))
            return await extract_data("", True, img)
        return await extract_data(text)
    except Exception as e:
        return JSONResponse({"Error": str(e)}, status_code=500)

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <head><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-900 text-white p-10 font-sans">
        <div class="max-w-2xl mx-auto bg-slate-800 p-8 rounded-3xl shadow-2xl border border-slate-700">
            <h1 class="text-2xl font-bold text-blue-400 mb-6 text-center">AI DATA ENTRY CORE</h1>
            <textarea id="t" class="w-full bg-slate-950 p-4 rounded-xl border border-slate-700 mb-4" rows="5" placeholder="Paste data here..."></textarea>
            <button onclick="run()" id="b" class="w-full bg-blue-600 py-3 rounded-xl font-bold hover:bg-blue-500 transition">Analyze with Gemini AI</button>
            <div id="r" class="mt-8 space-y-2"></div>
        </div>
        <script>
            async function run() {
                const b = document.getElementById('b'); b.innerText = "AI Thinking...";
                const fd = new FormData(); fd.append('text', document.getElementById('t').value);
                try {
                    const res = await fetch('/analyze', {method:'POST', body:fd});
                    const data = await res.json();
                    if(data.Error) document.getElementById('r').innerHTML = `<p class='text-red-500'>${data.Error}</p>`;
                    else document.getElementById('r').innerHTML = Object.entries(data).map(([k,v])=>`<div class='bg-slate-900 p-3 rounded-lg border border-slate-700'><b>${k}:</b> ${v}</div>`).join('');
                } catch(e) { alert("Network Error"); }
                finally { b.innerText = "Analyze with Gemini AI"; }
            }
        </script>
    </body>
    </html>
    """
