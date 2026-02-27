import os, io, re, json
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from PIL import Image
import google.generativeai as genai

# Render Environment Variables-la irundhu key-ai edukkirom
API_KEY = os.getenv("GEMINI_API_KEY")

# Connection Configuration
if API_KEY:
    # 'rest' transport and stable model name selection
    genai.configure(api_key=API_KEY, transport='rest')
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

app = FastAPI()

@app.post("/analyze")
async def analyze(text: str = Form(default="")):
    if not model:
        return {"Error": "API Key Missing. Check Render Settings."}
    try:
        # Prompt: Extracting fields as requested
        prompt = "Extract Name, Phone, Email, and Amount as a clean JSON object. If a field is missing, return 'N/A'."
        response = model.generate_content(f"{prompt}\nInput: {text}")
        
        # Regex to find JSON in AI response
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"Error": "AI did not return proper JSON format."}
    except Exception as e:
        # Inga dhaan 'v1beta' 404 error report aagirukkum
        return {"Error": f"Gemini Error: {str(e)}"}

@app.get("/", response_class=HTMLResponse)
def home():
    status = "✅ System Connected" if model else "❌ System Offline (Check API Key)"
    return f"""
    <html><body style="background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding-top:50px;">
        <div style="max-width:500px; margin:auto; background:#1e293b; padding:30px; border-radius:20px; border:1px solid #334155;">
            <h2 style="color:#3b82f6">AI DATA ENTRY ANALYZER</h2>
            <p style="font-size:12px; color:#94a3b8;">{status}</p>
            <textarea id="t" style="width:100%; height:120px; background:#020617; color:white; border-radius:10px; padding:15px; margin-bottom:20px; border:1px solid #444;" placeholder="Paste text here..."></textarea>
            <button onclick="run()" id="btn" style="width:100%; padding:15px; background:#2563eb; color:white; border:none; border-radius:10px; font-weight:bold; cursor:pointer;">ANALYZE NOW</button>
            <div id="res" style="margin-top:20px; text-align:left; background:#020617; padding:15px; border-radius:10px; color:#93c5fd; font-family:monospace;"></div>
        </div>
        <script>
            async function run() {{
                const b = document.getElementById('btn'); b.innerText = "Analyzing...";
                const fd = new FormData();
                fd.append('text', document.getElementById('t').value);
                try {{
                    const res = await fetch('/analyze', {{method:'POST', body:fd}});
                    const data = await res.json();
                    if(data.Error) document.getElementById('res').innerHTML = `<span style="color:red">${{data.Error}}</span>`;
                    else {{
                        let h = '<b>Results:</b><br><br>';
                        for(let [k,v] of Object.entries(data)) h += `<div><b>${{k}}:</b> ${{v}}</div>`;
                        document.getElementById('res').innerHTML = h;
                    }}
                }} catch(e) {{ alert("Check Network"); }}
                finally {{ b.innerText = "ANALYZE NOW"; }}
            }}
        </script>
    </body></html>
    """
    
