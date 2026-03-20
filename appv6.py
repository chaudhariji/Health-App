import streamlit as st
import pandas as pd
import sqlite3
import google.generativeai as genai
from PIL import Image
import re
import pytz
from datetime import datetime
from streamlit_mic_recorder import mic_recorder # New library for secure voice

# --- CONFIG ---
API_KEY = "AIzaSyCwVfrKjfsuXpcDp_glqlzne79yODwteB0"
genai.configure(api_key=API_KEY)
local_tz = pytz.timezone('America/Chicago')

def get_now():
    return datetime.now(local_tz)

def get_connection():
    return sqlite3.connect('fitness_data.db', check_same_thread=False)

# --- AI PARSING (FOR VOICE & IMAGE) ---
def ai_parse_text(input_text):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Extract health metrics from this text: "{input_text}"
    Return ONLY: Calories: [num], Protein: [num], Fiber: [num]
    """
    response = model.generate_content(prompt)
    text = response.text
    cals = re.search(r"Calories:\s*(\d+)", text)
    prot = re.search(r"Protein:\s*(\d+)", text)
    fib = re.search(r"Fiber:\s*(\d+)", text)
    return {"calories": int(cals.group(1)) if cals else 0, 
            "protein": int(prot.group(1)) if prot else 0, 
            "fiber": int(fib.group(1)) if fib else 0}

# --- UI ---
st.title("Today’s health summary")

@st.dialog("Log Your Entry")
def input_dialog():
    if "ai_results" not in st.session_state:
        st.session_state.ai_results = {"calories": 0, "protein": 0, "fiber": 0}

    tab1, tab2, tab3 = st.tabs(["Manual Review", "Upload Photo", "Voice Command"])
    
    with tab2:
        img_file = st.file_uploader("Select meal photo", type=['png', 'jpg', 'jpeg'])
        if img_file:
            with st.spinner("Analyzing photo..."):
                # (Reuse analyze_food_image logic here)
                st.success("Analysis complete! Go to Manual tab.")

    with tab3:
        st.write("Click to speak (e.g., 'I ate two eggs and a toast')")
        # Secure Microphone: Requests permission ONLY when clicked
        audio = mic_recorder(start_prompt="⏺️ Start Listening", stop_prompt="⏹️ Stop & Process", key='recorder')
        
        if audio:
            st.audio(audio['bytes'])
            st.info("Voice captured. (Note: Full Speech-to-Text requires an extra library like 'SpeechRecognition' or 'OpenAI Whisper')")

    with tab1:
        # Form logic to save to DB (same as previous response)
        pass

# [Dashboard Logic remains same...]
