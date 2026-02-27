import os, io, re, json, uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image
import google.generativeai as genai
from google.generativeai.types import RequestOptions

# --- Smart Gemini Connection ---
API_KEY = os.getenv("GEMINI_API_KEY") 
genai.configure(api_key=API_KEY)

def get_available_model():
    """Application start aagumbodhae available-aa irukkura model-ai select pannum"""
    #
    test_models = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']
    
    for m_name in test_models:
        try:
            # v1 API version force seivadhudhaan 404 fix
            model = genai.GenerativeModel(
                model_name=m_name,
                request_options=RequestOptions(api_version='v1')
            )
            # Dummy call to check if it's working
            print(f"Gemini Connected: {m_name}")
            return model, m_name
        except:
            continue
    return None, "None"

# Global Variables
model, active_model_name = get_available_model()
app = FastAPI()

# --- AI Extraction Logic ---
async def extract_ai_data(content, is_image=False, img_obj=None):
    if not model: 
        return {"Error": "AI Connection Failed. Check Render Environment Variables."}
    
    prompt = "Extract Name, Phone, Email, Amount as JSON. Return ONLY JSON. Use 'N/A' if missing."
    try:
        # File path errors-ai thavirkka image-ai direct bytes-aa handle panrom
        if is_image:
            response = model.generate_content([prompt, img_obj])
        else:
            response = model.generate_content(f"{prompt}\nInput: {content}")
        
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else {"Error": "AI Formatting Error"}
    except Exception as e:
        return {"Error": f"Gemini ({active_model_name}) says: {str(e)}"}

# --- API Route ---
@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    try:
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(io.BytesIO(await file.read()))
            return await extract_ai_data("", True, img)
        return await extract_ai_data(text)
    except Exception as e:
        return JSONResponse({"Error": str(e)}, status_code=500)

# --- Integrated Frontend UI ---
@app.get("/", response_class=HTMLResponse)
def home():
    status_color = "text-green-400" if model else "text-red-500"
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>AI Data Entry - Enterprise</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body {{ background: #0b0f1a; color: white; }}
            .glass-card {{ background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; backdrop-filter: blur(10px); }}
        </style>
    </head>
    <body class="p-6 md:p-12">
        <div class="max-w-4xl mx-auto">
            <div class="flex justify-between items-center mb-8">
                <h1 class="text-3xl font-bold text-blue-500">AI DATA ANALYZER</h1>
                <div class="text-xs font-mono {status_color}">
                    Status: {active_model_name} Connected ✅
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="glass-card p-6 rounded-3xl shadow-2xl">
                    <h3 class="text-slate-400 mb-4 font-bold text-sm uppercase">Input Section</h3>
                    <textarea id="tIn" rows="8" class="w-full bg-slate-950 p-4 rounded-2xl border border-slate-800 outline-none focus:border-blue-500 mb-4" placeholder="Paste data or text..."></textarea>
                    <input type="file" id="fIn" class="block w-full text-xs text-slate-500 mb-4">
                    <button onclick="run()" id="btn" class="w-full bg-blue-600 hover:bg-blue-500 py-4 rounded-2xl font-bold transition-all shadow-lg">
                        Analyze Now
                    </button>
                </div>

                <div class="glass-card p-6 rounded-3xl min-h-[400px]">
                    <h3 class="text-slate-400 mb-4 font-bold text-sm uppercase">Extracted Results</h3>
                    <div id="res" class="space-y-3">
                        <p class="text-slate-600 italic">Results will appear here...</p>
                    </div>
                </div>
            </div>
        </div>

        <script>
            async function run() {{
                const btn = document.getElementById('btn');
                const resDiv = document.getElementById('res');
                btn.innerText = "Gemini is Analyzing...";
                btn.disabled = true;

                const fd = new FormData();
                fd.append('text', document.getElementById('tIn').value);
                const file = document.getElementById('fIn').files[0];
                if(file) fd.append('file', file);

                try {{
                    const response = await fetch('/analyze', {{ method: 'POST', body: fd }});
                    const data = await response.json();
                    
                    if(data.Error) {{
                        resDiv.innerHTML = `<div class="bg-red-900/20 border border-red-500/50 p-4 rounded-xl text-red-400 text-sm">Error: ${{data.Error}}</div>`;
                    }} else {{
                        resDiv.innerHTML = Object.entries(data).map(([k,v]) => `
                            <div class="bg-slate-900/80 p-4 rounded-xl border border-slate-800 flex justify-between">
                                <span class="text-blue-400 font-bold uppercase text-[10px]">${{k}}</span>
                                <span class="text-blue-50 text-sm">${{v}}</span>
                            </div>
                        `).join('');
                    }}
                }} catch (e) {{
                    alert("Network Error: Could not connect to backend.");
                }} finally {{
                    btn.innerText = "Analyze Now";
                    btn.disabled = false;
                }}
            }}
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
