import os, io, re, json, uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from PIL import Image
import google.generativeai as genai
from google.generativeai.types import RequestOptions

# API Key - Render Environment Variables-la irundhu edukkirom
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    # FORCING V1 STABLE VERSION - Indha oru line dhaan unga 404 error-ai fix pannum
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        request_options=RequestOptions(api_version='v1')
    )
else:
    model = None

app = FastAPI()

@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    if not model:
        return {"Error": "API Key missing in Render settings!"}
    try:
        prompt = "Extract Name, Phone, Email, Amount as JSON. Return ONLY JSON."
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img = Image.open(io.BytesIO(await file.read()))
            response = model.generate_content([prompt, img])
        else:
            response = model.generate_content(f"{prompt}\nInput: {text}")
        
        # AI response-il irundhu JSON-ai matum pirikka
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"Error": "AI Format Error - Try again"}
    except Exception as e:
        return {"Error": str(e)}

@app.get("/", response_class=HTMLResponse)
def home():
    status_msg = "✅ Connected to Gemini Stable" if model else "❌ Check Render API Key"
    return f"""
    <html><head><title>AI Data Analyzer</title>
    <style>
        body {{ background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:50px; }}
        .box {{ background:#1e293b; padding:30px; border-radius:20px; max-width:500px; margin:auto; border:1px solid #334155; }}
        textarea {{ width:100%; height:120px; background:#020617; color:white; border-radius:10px; padding:10px; margin:15px 0; border:1px solid #444; }}
        button {{ width:100%; padding:15px; background:#2563eb; color:white; border:none; border-radius:12px; font-weight:bold; cursor:pointer; }}
        #res {{ margin-top:20px; text-align:left; background:#020617; padding:15px; border-radius:10px; color:#93c5fd; font-family:monospace; }}
    </style></head>
    <body>
        <div class="box">
            <h2 style="color:#3b82f6">Gemini Data Analysis</h2>
            <p style="font-size:11px; color:#94a3b8;">{status_msg}</p>
            <textarea id="t" placeholder="Enter transaction details or data here..."></textarea>
            <input type="file" id="f" style="margin-bottom:15px; display:block; font-size:12px;">
            <button onclick="run()" id="btn">Analyze Now</button>
            <div id="res">Waiting for data...</div>
        </div>
        <script>
            async function run() {{
                const b = document.getElementById('btn'); b.innerText = "Processing...";
                const fd = new FormData();
                fd.append('text', document.getElementById('t').value);
                if(document.getElementById('f').files[0]) fd.append('file', document.getElementById('f').files[0]);
                try {{
                    const res = await fetch('/analyze', {{method:'POST', body:fd}});
                    const data = await res.json();
                    if(data.Error) document.getElementById('res').innerHTML = `<span style="color:red">${{data.Error}}</span>`;
                    else {{
                        let html = '<b>Extracted Data:</b><br><br>';
                        for(let [k,v] of Object.entries(data)) html += `<div><b>${{k}}:</b> ${{v}}</div>`;
                        document.getElementById('res').innerHTML = html;
                    }}
                }} catch(e) {{ alert("Connection Error"); }}
                finally {{ b.innerText = "Analyze Now"; }}
            }}
        </script>
    </body></html>
    """
