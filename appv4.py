import streamlit as st
import pandas as pd
import sqlite3
import google.generativeai as genai
from PIL import Image
import re
from datetime import datetime, timedelta

# --- API SETUP ---
# It's best to use st.secrets["GEMINI_API_KEY"], but I've used your provided key here for immediate testing.
API_KEY = "AIzaSyCwVfrKjfsuXpcDp_glqlzne79yODwteB0"
genai.configure(api_key=API_KEY)

def init_db():
    conn = sqlite3.connect('fitness_data.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS daily_metrics 
                 (date TEXT UNIQUE, weight FLOAT, calories_in INTEGER, 
                  protein INTEGER, fiber INTEGER, water FLOAT, calories_burnt INTEGER)''')
    conn.commit()
    return conn

conn = init_db()

# --- AI IMAGE PROCESSING ---
def analyze_food_image(uploaded_file):
    model = genai.GenerativeModel('gemini-1.5-flash')
    img = Image.open(uploaded_file)
    prompt = """
    Identify the food in this image. Estimate the totals for the entire plate.
    Return ONLY these three lines:
    Calories: [number]
    Protein: [number]
    Fiber: [number]
    """
    response = model.generate_content([prompt, img])
    text = response.text
    
    # Extract numbers using Regular Expressions
    cals = re.search(r"Calories:\s*(\d+)", text)
    prot = re.search(r"Protein:\s*(\d+)", text)
    fib = re.search(r"Fiber:\s*(\d+)", text)
    
    return {
        "calories": int(cals.group(1)) if cals else 0,
        "protein": int(prot.group(1)) if prot else 0,
        "fiber": int(fib.group(1)) if fib else 0
    }

# --- UI ---
st.markdown("<style>.stButton button {float: right; border-radius: 10px; border: 1px solid #dcdcdc;}</style>", unsafe_allow_html=True)

col_title, col_btn = st.columns([5, 1])
with col_title:
    st.title("Today’s health summary")

@st.dialog("Log Your Entry")
def input_dialog():
    # Initialize session state for AI results if not present
    if "ai_results" not in st.session_state:
        st.session_state.ai_results = {"calories": 0, "protein": 0, "fiber": 0}

    tab1, tab2 = st.tabs(["Manual / Review", "Photo Log (AI)"])
    
    with tab2:
        img_file = st.camera_input("Snap your food")
        if img_file:
            with st.spinner("AI is calculating..."):
                st.session_state.ai_results = analyze_food_image(img_file)
                st.success("Analysis complete! Review the 'Manual' tab to save.")

    with tab1:
        latest = pd.read_sql_query("SELECT weight FROM daily_metrics ORDER BY date DESC LIMIT 1", conn)
        curr_w = latest['weight'].iloc[0] if not latest.empty else 175.0
        
        with st.form("Daily Totals", clear_on_submit=True):
            w = st.number_input("Weight (lbs)", value=curr_w, step=0.1)
            # These now default to the AI results if a photo was taken
            c_in = st.number_input("Calories In", value=st.session_state.ai_results["calories"])
            p = st.number_input("Protein (g)", value=st.session_state.ai_results["protein"])
            f = st.number_input("Fiber (g)", value=st.session_state.ai_results["fiber"])
            w_l = st.number_input("Water (L)", min_value=0.0, step=0.5)
            c_out = st.number_input("Calories Burnt", min_value=0)
            
            if st.form_submit_button("Confirm & Save"):
                today = datetime.now().strftime('%Y-%m-%d')
                conn.execute("""INSERT INTO daily_metrics VALUES (?, ?, ?, ?, ?, ?, ?) 
                             ON CONFLICT(date) DO UPDATE SET 
                             weight=excluded.weight, calories_in=excluded.calories_in, 
                             protein=excluded.protein, fiber=excluded.fiber, 
                             water=excluded.water, calories_burnt=excluded.calories_burnt""", 
                             (today, w, c_in, p, f, w_l, c_out))
                conn.commit()
                # Reset AI results after saving
                st.session_state.ai_results = {"calories": 0, "protein": 0, "fiber": 0}
                st.rerun()

with col_btn:
    if st.button("**+**"):
        input_dialog()

# [Previous Dashboard code goes here...]
