import streamlit as st
import pandas as pd
import sqlite3
import google.generativeai as genai
from PIL import Image
import re
import pytz
from datetime import datetime
from streamlit_mic_recorder import mic_recorder

# --- 1. CONFIGURATION & API SETUP ---
# Replace with st.secrets["GEMINI_API_KEY"] once you set it in Streamlit Cloud
API_KEY = "AIzaSyCwVfrKjfsuXpcDp_glqlzne79yODwteB0"
genai.configure(api_key=API_KEY)

# Force Illinois Time (Central Time)
local_tz = pytz.timezone('America/Chicago')

def get_now():
    return datetime.now(local_tz)

def get_connection():
    return sqlite3.connect('fitness_data.db', check_same_thread=False)

# --- 2. DATABASE INITIALIZATION ---
def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS daily_metrics 
                 (date TEXT UNIQUE, weight FLOAT, calories_in INTEGER, 
                  protein INTEGER, fiber INTEGER, water FLOAT, calories_burnt INTEGER)''')
    conn.commit()

init_db()

# --- 3. AI PROCESSING LOGIC ---
def analyze_food_image(uploaded_file):
    model = genai.GenerativeModel('gemini-1.5-flash')
    img = Image.open(uploaded_file)
    prompt = """Identify the food. Provide an estimate for the full plate.
    Return ONLY: Calories: [num], Protein: [num], Fiber: [num]"""
    response = model.generate_content([prompt, img])
    text = response.text
    cals = re.search(r"Calories:\s*(\d+)", text)
    prot = re.search(r"Protein:\s*(\d+)", text)
    fib = re.search(r"Fiber:\s*(\d+)", text)
    return {
        "calories": int(cals.group(1)) if cals else 0,
        "protein": int(prot.group(1)) if prot else 0,
        "fiber": int(fib.group(1)) if fib else 0
    }

# --- 4. INPUT DIALOG (POPS UP FROM SIDEBAR) ---
@st.dialog("Log Health Data")
def input_dialog():
    if "ai_results" not in st.session_state:
        st.session_state.ai_results = {"calories": 0, "protein": 0, "fiber": 0}

    tab1, tab2, tab3 = st.tabs(["Review & Save", "Photo Upload", "Voice Log"])
    
    with tab2:
        st.write("Privacy: Accesses your files/camera only when you click below.")
        img_file = st.file_uploader("Upload meal photo", type=['png', 'jpg', 'jpeg'])
        if img_file:
            with st.spinner("AI analyzing food..."):
                st.session_state.ai_results = analyze_food_image(img_file)
                st.success("Analysis complete! Go to the 'Review' tab.")

    with tab3:
        st.write("Tap to speak (e.g., 'Lunch was 500 calories and 40 grams of protein')")
        audio = mic_recorder(start_prompt="⏺️ Start Listening", stop_prompt="⏹️ Stop & Process", key='recorder')
        if audio:
            st.info("Voice data received. Please verify metrics in the Review tab.")

    with tab1:
        conn = get_connection()
        latest = pd.read_sql_query("SELECT weight FROM daily_metrics ORDER BY date DESC LIMIT 1", conn)
        curr_w = latest['weight'].iloc[0] if not latest.empty else 175.0
        
        with st.form("HealthForm", clear_on_submit=True):
            w = st.number_input("Current Weight (lbs)", value=float(curr_w), step=0.1)
            c_in = st.number_input("Calories Consumed", value=st.session_state.ai_results["calories"])
            p = st.number_input("Protein (g)", value=st.session_state.ai_results["protein"])
            f = st.number_input("Fiber (g)", value=st.session_state.ai_results["fiber"])
            w_l = st.number_input("Water (L)", min_value=0.0, step=0.5)
            c_out = st.number_input("Calories Burnt", min_value=0)
            
            if st.form_submit_button("Confirm & Save"):
                today_str = get_now().strftime('%Y-%m-%d')
                conn.execute("""INSERT INTO daily_metrics VALUES (?, ?, ?, ?, ?, ?, ?) 
                             ON CONFLICT(date) DO UPDATE SET 
                             weight=excluded.weight, calories_in=excluded.calories_in, 
                             protein=excluded.protein, fiber=excluded.fiber, 
                             water=excluded.water, calories_burnt=excluded.calories_burnt""", 
                             (today_str, w, c_in, p, f, w_l, c_out))
                conn.commit()
                st.session_state.ai_results = {"calories": 0, "protein": 0, "fiber": 0}
                st.rerun()

# --- 5. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.header("Actions")
    if st.button("➕ **Log New Entry**", use_container_width=True):
        input_dialog()
    st.divider()
    st.caption("Location: Naperville, IL")

# --- 6. MAIN DASHBOARD ---
st.title("Today’s health summary")

conn = get_connection()
today_str = get_now().strftime('%Y-%m-%d')
df_today = pd.read_sql_query(f"SELECT * FROM daily_metrics WHERE date='{today_str}'", conn)

if not df_today.empty:
    row = df_today.iloc[0]
    
    # METRIC CALCULATIONS
    net_cals = row['calories_in'] - row['calories_burnt']
    predicted_change = net_cals / 3500  # 3500 kcal rule
    
    # UI: Weight & Calories Side-by-Side
    c1, c2 = st.columns(2)
    c1.metric("Net Weight Change", f"{predicted_change:+.2f} lbs")
    c2.metric("Net Calories", f"{net_cals} kcal", f"In: {row['calories_in']} | Out: {row['calories_burnt']}")

    st.divider()

    # UI: Macros Side-by-Side
    c3, c4, c5 = st.columns(3)
    c3.metric("Protein", f"{row['protein']}g", f"Target: {int(row['weight'])}g")
    c4.metric("Fiber", f"{row['fiber']}g")
    c5.metric("Water", f"{row['water']}L")
else:
    st.info(f"Welcome! No data logged for today ({today_str}). Open the sidebar to begin.")

# --- 7. TRENDS & ANALYTICS ---
history = pd.read_sql_query("SELECT * FROM daily_metrics ORDER BY date ASC", conn)
if not history.empty:
    st.divider()
    st.subheader("Weight Trend Analysis")
    
    # Absolute Change Calculation for the graph header
    abs_change = history['weight'].iloc[-1] - history['weight'].iloc[0]
    st.write(f"### Total Absolute Change: **{abs_change:+.1f} lbs**")
    
    # Custom Graph
    st.line_chart(history.set_index('date')['weight'])
