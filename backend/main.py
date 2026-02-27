import os, io, re, json, uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from PIL import Image
import google.generativeai as genai

# API Key - Render dashboard variables-la irundhu edukkirom
API_KEY = os.getenv("GEMINI_API_KEY")

# Connection Configuration
if API_KEY:
    # transport='rest' nu kuduppadhu connection-ai innum stable aakkum
    genai.configure(api_key=API_KEY, transport='rest')
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

app = FastAPI()

@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    if not model:
        return {"Error": "API Key check failed. Update GEMINI_API_KEY in Render."}
    try:
        # Prompt definition
        prompt = "Extract Name, Phone, Email, Amount as JSON. Return ONLY valid JSON."
        
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(io.BytesIO(await file.read()))
            response = model.generate_content([prompt, img])
        else:
            response = model.generate_content(f"{prompt}\nInput: {text}")
        
        # JSON extraction logic
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"Error": "AI response format error. Try again."}
    except Exception as e:
        # Direct error reporting to identify issues
        return {"Error": f"Gemini Error: {str(e)}"}

@app.get("/", response_class=HTMLResponse)
def home():
    status = "✅ Connected" if model else "❌ API Key Missing"
    return f"""
    <html><body style="background:#0f172a; color:white; padding:50px; font-family:sans-serif; text-align:center;">
        <div style="max-width:500px; margin:auto; background:#1e293b; padding:40px; border-radius:30px; border:2px solid #334155;">
            <h1 style="color:#3b82f6; letter-spacing:1px;">AI DATA ENTRY</h1>
            <p style="font-size:12px; color:#94a3b8; margin-bottom:20px;">System Status: {status}</p>
            <textarea id="t" style="width:100%; height:120px; background:#020617; color:white; border-radius:15px; padding:15px; margin-bottom:20px; border:1px solid #444;" placeholder="Paste text here..."></textarea>
            <button onclick="run()" id="btn" style="width:100%; padding:18px; background:#2563eb; color:white; border:none; border-radius:15px; font-weight:bold; cursor:pointer; font-size:16px;">ANALYZE NOW</button>
            <div id="res" style="margin-top:30px; text-align:left; background:#020617; padding:20px; border-radius:15px; border-left:4px solid #3b82f6; font-family:monospace;"></div>
        </div>
        <script>
            async function run() {{
                const b = document.getElementById('btn'); b.innerText = "Processing..."; b.disabled = true;
                const fd = new FormData();
                fd.append('text', document.getElementById('t').value);
                try {{
                    const res = await fetch('/analyze', {{method:'POST', body:fd}});
                    const data = await res.json();
                    if(data.Error) document.getElementById('res').innerHTML = `<span style="color:#f87171">${{data.Error}}</span>`;
                    else {{
                        let html = '<div style="color:#60a5fa; margin-bottom:10px;">✔ Extraction Complete:</div>';
                        for(let [k,v] of Object.entries(data)) {{
                            html += `<div style="margin:5px 0;"><b>${{k}}:</b> ${{v}}</div>`;
                        }}
                        document.getElementById('res').innerHTML = html;
                    }}
                }} catch(e) {{ alert("Network Error. Check Render Logs."); }}
                finally {{ b.innerText = "ANALYZE NOW"; b.disabled = false; }}
            }}
        </script>
    </body></html>
    """
    
