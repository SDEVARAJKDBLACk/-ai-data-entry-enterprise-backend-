import os
import google.generativeai as genai
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# API Key check
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    # 404 varaama irukka 'gemini-1.5-flash' use pannuvom
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
    <head>
        <title>AI Chatbot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding:20px; }
            #chatbox { background:#1e293b; padding:15px; border-radius:12px; max-width:500px; margin:auto; height:400px; overflow-y:auto; text-align:left; border:1px solid #334155; }
            .input-area { max-width:500px; margin:20px auto; display:flex; gap:10px; }
            input { flex:1; padding:12px; border-radius:8px; border:none; outline:none; color:black; }
            button { padding:12px 24px; background:#3b82f6; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:bold; }
        </style>
    </head>
    <body>
        <h2>🤖 Gemini AI Chatbot</h2>
        <div id="chatbox"><p style="color:#64748b;">System Ready. Type a message...</p></div>
        <div class="input-area">
            <input type="text" id="userInput" placeholder="Say Hi...">
            <button onclick="send()">SEND</button>
        </div>
        <script>
            async function send() {
                const input = document.getElementById('userInput');
                const chat = document.getElementById('chatbox');
                const msg = input.value;
                if(!msg) return;
                chat.innerHTML += `<div><b>You:</b> ${msg}</div>`;
                input.value = "";
                try {
                    const formData = new FormData();
                    formData.append('message', msg);
                    const response = await fetch('/chat', { method: 'POST', body: formData });
                    const data = await response.json();
                    chat.innerHTML += `<div style="color:#60a5fa;"><b>AI:</b> ${data.reply}</div>`;
                } catch(e) {
                    chat.innerHTML += `<p style="color:red;">Error: Server Busy.</p>`;
                }
                chat.scrollTop = chat.scrollHeight;
            }
        </script>
    </body>
    </html>
    """

@app.post("/chat")
async def chat(message: str = Form(...)):
    if not model:
        return {"reply": "API Key not configured."}
    try:
        response = model.generate_content(message)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Gemini Error: {str(e)}"}
        
