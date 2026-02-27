import os
import google.generativeai as genai
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

# API Key - Render settings-la GEMINI_API_KEY nu variable irukkanum
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
    <head><title>Simple AI Bot</title></head>
    <body style="background:#121212; color:white; font-family:sans-serif; text-align:center; padding:50px;">
        <h2>🤖 Simple AI Chatbot</h2>
        <div id="chatbox" style="background:#1e1e1e; padding:20px; border-radius:10px; max-width:500px; margin:auto; height:300px; overflow-y:auto; text-align:left; border:1px solid #333;">
            <p style="color:#888;">AI: Hello! Ask me anything...</p>
        </div>
        <br>
        <input type="text" id="userInput" style="width:350px; padding:10px; border-radius:5px; border:none;" placeholder="Type message...">
        <button onclick="sendMessage()" style="padding:10px 20px; background:blue; color:white; border:none; border-radius:5px; cursor:pointer;">Send</button>

        <script>
            async function sendMessage() {
                const input = document.getElementById('userInput');
                const chat = document.getElementById('chatbox');
                const msg = input.value;
                if(!msg) return;

                chat.innerHTML += `<p><b>You:</b> ${msg}</p>`;
                input.value = "";

                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `message=${encodeURIComponent(msg)}`
                });
                const data = await response.json();
                chat.innerHTML += `<p style="color:#00ff00;"><b>AI:</b> ${data.reply}</p>`;
                chat.scrollTop = chat.scrollHeight;
            }
        </script>
    </body>
    </html>
    """

@app.post("/chat")
async def chat(message: str = Form(...)):
    try:
        response = model.generate_content(message)
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}
        
