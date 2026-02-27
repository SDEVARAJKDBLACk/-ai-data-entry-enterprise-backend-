import os, io, re, json, uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from PIL import Image
import google.generativeai as genai

# API Key - Render Environment-il irundhu edukkirom (Safe Method)
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

app = FastAPI()

@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    if not model:
        return {"Error": "API Key not found in Render Environment Variables!"}
    try:
        prompt = "Extract Name, Phone, Email, Amount as JSON. Return ONLY JSON."
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(io.BytesIO(await file.read()))
            response = model.generate_content([prompt, img])
        else:
            response = model.generate_content(f"{prompt}\nInput: {text}")
        
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else {"Error": "AI format error"}
    except Exception as e:
        return {"Error": str(e)}

@app.get("/", response_class=HTMLResponse)
def home():
    status = "✅ Connected" if model else "❌ API Key Missing in Render"
    return f"""
    <html><body style="background:#0f172a; color:white; padding:50px; font-family:sans-serif; text-align:center;">
        <div style="max-width:500px; margin:auto; background:#1e293b; padding:30px; border-radius:20px; border:1px solid #334155;">
            <h2 style="color:#3b82f6 text-transform:uppercase;">AI Data Analyzer</h2>
            <p style="font-size:12px; color:#94a3b8;">Status: {status}</p>
            <textarea id="t" style="width:100%; height:100px; background:#020617; color:white; border-radius:10px; padding:10px; margin:15px 0; border:1px solid #334155;"></textarea>
            <button onclick="run()" id="btn" style="width:100%; padding:15px; background:#2563eb; color:white; border:none; border-radius:12px; font-weight:bold; cursor:pointer;">Start Analysis</button>
            <div id="res" style="margin-top:20px; text-align:left; background:#020617; padding:15px; border-radius:10px; font-size:13px;"></div>
        </div>
        <script>
            async function run() {{
                const b = document.getElementById('btn'); b.innerText = "Analyzing...";
                const fd = new FormData();
                fd.append('text', document.getElementById('t').value);
                try {{
                    const res = await fetch('/analyze', {{method:'POST', body:fd}});
                    const data = await res.json();
                    document.getElementById('res').innerHTML = data.Error ? `<span style="color:red">${{data.Error}}</span>` : `<pre style="color:#93c5fd">${{JSON.stringify(data, null, 2)}}</pre>`;
                }} catch(e) {{ alert("Check Render Logs"); }}
                finally {{ b.innerText = "Start Analysis"; }}
            }}
        </script>
    </body></html>
    """
