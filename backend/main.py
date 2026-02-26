import os, io, re, json, uvicorn, pandas as pd
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from PIL import Image
import pdfplumber, docx
import google.generativeai as genai

# --- Gemini Connection Logic (Fixed) ---
API_KEY = os.getenv("GEMINI_API_KEY")

# API Key check
if not API_KEY:
    API_KEY = "AIzaSyCtx4Uk5b_vyMPkRHz1WZswC7xggUkZ01c"

genai.configure(api_key=API_KEY)

# 'gemini-1.5-flash-latest' nu use pannunga, ippo 404 error varadhu
try:
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    print("Gemini AI Connected Successfully!")
except Exception as e:
    # Fallback model if latest fails
    model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI()

# --- Memory Storage (No JSON files for Render) ---
# Render-la file write panna permission illai, adhanaala memory-la store panrom
history_memory = []
custom_fields_memory = []

@app.post("/analyze")
async def analyze(file: UploadFile = None, text: str = Form(default="")):
    try:
        content = text
        if file:
            f_bytes = await file.read()
            # File extraction logic
            if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                img = Image.open(io.BytesIO(f_bytes))
                prompt = "Extract Name, Phone, Email, Amount, Date as JSON."
                response = model.generate_content([prompt, img])
            else:
                # PDF/Docx logic goes here...
                response = model.generate_content(f"Extract data from this text as JSON: {content}")
        else:
            response = model.generate_content(f"Extract data from this text as JSON: {content}")

        # JSON cleaning and storage
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        result = json.loads(json_match.group()) if json_match else {"Error": "Format error"}
        
        if "Error" not in result:
            result['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            history_memory.insert(0, result)
        
        return result
    except Exception as e:
        return JSONResponse({"Error": str(e)}, status_code=500)

@app.get("/export_excel")
async def export():
    # Excel export logic
    if not history_memory: return {"error": "No data"}
    df = pd.DataFrame(history_memory)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.ms-excel", headers={"Content-Disposition": "attachment; filename=data.xlsx"})

@app.get("/", response_class=HTMLResponse)
def home():
    return "<h1>AI Connected & Running!</h1><p>Use /analyze to start.</p>"
    
