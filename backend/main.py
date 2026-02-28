import streamlit as st
import openai
import PyPDF2
import docx
from PIL import Image
import pytesseract
import io
import json
import pandas as pd

# --- Page Config & UI Injection ---
st.set_page_config(page_title="AI Data Entry - Automated Data Worker", layout="centered")

# Screenshot-la irukkira athe Dark UI design-ai CSS moolama kondu varom
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #0b0e14;
        color: #e2e8f0;
    }
    /* Card/Container Style */
    div.stBlock {
        background-color: #161b22;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
    }
    /* Input Boxes */
    textarea, input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border-radius: 8px !important;
    }
    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        border: none;
    }
    .analyze-btn { background-color: #00bcd4 !important; color: white !important; } /* Cyan */
    .clear-btn { background-color: #3f51b5 !important; color: white !important; }   /* Blue/Purple */
    .export-btn { background-color: #673ab7 !important; color: white !important; }  /* Deep Purple */
    
    /* Headers */
    h1, h2, h3 { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- Session States ---
if 'history' not in st.session_state:
    st.session_state.history = []
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- App Logic ---
def extract_text(file):
    fname = file.name.lower()
    if fname.endswith('.pdf'):
        return "".join([p.extract_text() for p in PyPDF2.PdfReader(file).pages])
    elif fname.endswith('.docx'):
        return "\n".join([p.text for p in docx.Document(file).paragraphs])
    elif fname.endswith(('.png', '.jpg', '.jpeg')):
        return pytesseract.image_to_string(Image.open(file))
    else:
        return file.read().decode('utf-8')

# --- Login Phase ---
if not st.session_state.logged_in:
    st.title("🔐 Login")
    user = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    if st.button("Login"):
        if user == "admin" and pw == "admin123":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid Login")
else:
    # --- UI Layout Starts ---
    st.title("AI Data Entry – Automated Data Worker")

    # Section 1: Upload & Input
    with st.container():
        st.markdown("### 📂 Upload text / notes / message / PDF / Word")
        uploaded_file = st.file_uploader("Choose file", type=['pdf', 'docx', 'png', 'jpg', 'jpeg', 'txt'], label_visibility="collapsed")
        
        st.markdown("### Enter or paste input")
        user_input = st.text_area("", height=200, label_visibility="collapsed")
        
        col1, col2, col3, _ = st.columns([1, 1, 1.5, 4])
        analyze = col1.button("Analyze")
        clear = col2.button("Clear")
        export = col3.button("Export Excel")

    # Section 2: Extracted Data
    st.markdown("---")
    st.markdown("### Extracted Data:")
    col_f, col_v = st.columns(2)
    col_f.write("**Field**")
    col_v.write("**Values**")
    
    # Placeholder for Results
    if analyze:
        # Inga unga OpenAI logic-ai add pannalam
        st.info("Analyzing data... (Connect your OpenAI Key to see results)")

    # Section 3: Custom Fields
    st.markdown("---")
    st.markdown("### ➕ Custom Fields")
    c1, c2, c3 = st.columns([2, 2, 1])
    c1.text_input("Field name", placeholder="e.g. GST Number", label_visibility="collapsed")
    c2.text_input("Value", placeholder="e.g. 22AAAAA0000A1Z5", label_visibility="collapsed")
    c3.button("Add")

    # Section 4: History
    st.markdown("---")
    st.markdown("### 🕒 Last 10 Analysis")
    if st.session_state.history:
        st.table(st.session_state.history)
    else:
        st.write("No recent analysis found.")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
        
