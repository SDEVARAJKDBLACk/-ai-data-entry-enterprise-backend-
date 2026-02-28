import streamlit as st
import openai
import PyPDF2
import docx
from PIL import Image
import pytesseract
import io
import json
import pandas as pd
import os
from datetime import datetime

# --- Page Config & UI ---
st.set_page_config(page_title="AI Data Entry Pro", layout="centered")

# Custom CSS for Dark UI (As per your screenshot)
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e2e8f0; }
    div.stBlock { background-color: #161b22; padding: 20px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #30363d; }
    textarea, input { background-color: #ffffff !important; color: #000000 !important; border-radius: 8px !important; }
    .stButton>button { border-radius: 8px; font-weight: 600; width: 100%; height: 45px; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) button { background-color: #00bcd4 !important; color: white; } 
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button { background-color: #3f51b5 !important; color: white; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(3) button { background-color: #673ab7 !important; color: white; }
    </style>
    """, unsafe_allow_html=True)

# Session state initialize
if 'history' not in st.session_state: st.session_state.history = []
if 'extracted_data' not in st.session_state: st.session_state.extracted_data = None

# --- Functions ---
def ai_process(text, fields_list):
    # API Key check (Render Environment Variable or Sidebar)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"Error": "OpenAI API Key Missing! Render Settings-la add pannunga."}
    
    openai.api_key = api_key
    prompt = f"""
    Extract the following fields from the text: {fields_list}.
    Text: {text}
    Return the result ONLY as a JSON object.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o", # Best for extraction
            messages=[{"role": "system", "content": "You are a professional data entry assistant."},
                      {"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"Error": str(e)}

# --- UI Layout ---
st.title("AI Data Entry – Automated Data Worker")

with st.container():
    st.markdown("### 📂 Upload file or Paste Input")
    file = st.file_uploader("", type=['pdf','docx','png','jpg','jpeg','txt'], label_visibility="collapsed")
    raw_input = st.text_area("Input area", height=150, label_visibility="collapsed", placeholder="Paste your data here...")
    
    c1, c2, c3 = st.columns([1, 1, 1.2])
    
    if c1.button("Analyze"):
        source_text = raw_input # Priority to text area
        if not source_text and file:
            # File extraction logic (munaadi sonnathu pola)
            source_text = "File content extraction here..." 
            
        if source_text:
            with st.spinner("AI is finding fields..."):
                # Default extraction fields
                result = ai_process(source_text, "Name, Date, Amount, Address, Phone")
                if "Error" in result:
                    st.error(result["Error"])
                else:
                    st.session_state.extracted_data = result
                    st.session_state.history.append({"Time": datetime.now().strftime("%H:%M"), **result})
                    st.rerun() # Refresh panna thaan display aagum
        else:
            st.warning("Data ethuvum illai!")

# --- Display Results ---
st.markdown("---")
st.markdown("### Extracted Data:")
if st.session_state.extracted_data:
    # Displaying as a neat table/list
    for key, val in st.session_state.extracted_data.items():
        st.write(f"**{key}:** {val}")
else:
    st.info("Results will appear here.")

# Custom Fields & History (Bottom sections)
st.markdown("---")
st.subheader("🕒 Last 10 Analysis")
if st.session_state.history:
    st.dataframe(pd.DataFrame(st.session_state.history).tail(10))
        
