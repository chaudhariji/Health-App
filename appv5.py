import streamlit as st
import pandas as pd
import sqlite3
import google.generativeai as genai
from PIL import Image
import re
from datetime import datetime, timedelta

# --- API & DB SETUP ---
API_KEY = "AIzaSyCwVfrKjfsuXpcDp_glqlzne79yODwteB0"
genai.configure(api_key=API_KEY)

def get_connection():
    return sqlite3.connect('fitness_data.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS daily_metrics 
                 (date TEXT UNIQUE, weight FLOAT, calories_in INTEGER, 
                  protein INTEGER, fiber INTEGER, water FLOAT, calories_burnt INTEGER)''')
    conn.commit()
    return conn

init_db()

# --- CSS FOR UI ---
st.markdown("<style>.stButton button {float: right; border-radius: 10px;}</style>", unsafe_allow_html=True)

# --- HEADER ---
col_title, col_btn = st.columns([5, 1])
with col_title:
    st.title("Today’s health summary")

# --- INPUT DIALOG ---
@st.dialog("Log Your Entry")
def input_dialog():
    if "ai_results" not in st.session_state:
        st.session_state.ai_results = {"calories": 0, "protein": 0, "fiber": 0}

    tab1, tab2 = st.tabs(["Manual / Review", "Photo Log (AI)"])
    
    with tab2:
        img_file = st.camera_input("Snap your food")
        if img_file:
            # AI Logic remains the same...
            pass

    with tab1:
        conn = get_connection()
        latest = pd.read_sql_query("SELECT weight FROM daily_metrics ORDER BY date DESC LIMIT 1", conn)
        curr_w = latest['weight'].iloc[0] if not latest.empty else 175.0
        
        with st.form("Daily Totals"):
            w = st.number_input("Weight (lbs)", value=curr_w, step=0.1)
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
                st.session_state.ai_results = {"calories": 0, "protein": 0, "fiber": 0}
                st.rerun() # Force the whole app to refresh with new data

with col_btn:
    if st.button("**+**"):
        input_dialog()

# --- DASHBOARD LOGIC (The Fix) ---
conn = get_connection()
today_str = datetime.now().strftime('%Y-%m-%d')

# Try to get today's data
df_today = pd.read_sql_query(f"SELECT * FROM daily_metrics WHERE date='{today_str}'", conn)

if not df_today.empty:
    row = df_today.iloc[0]
    # Prediction Formula: 3500 kcal = 1 lb
    net_cals = row['calories_in'] - row['calories_burnt']
    predicted_change = net_cals / 3500
    
    c1, c2 = st.columns(2)
    c1.metric("Net Weight Change", f"{predicted_change:+.2f} lbs")
    c2.metric("Net Calories", f"{net_cals} kcal")

    st.divider()

    c3, c4, c5 = st.columns(3)
    c3.metric("Protein", f"{row['protein']}g", f"Target: {int(row['weight'])}g")
    c4.metric("Fiber", f"{row['fiber']}g")
    c5.metric("Water", f"{row['water']}L")
else:
    st.info("No data logged for today yet. Use the + button to start.")

# --- TREND GRAPH ---
st.divider()
history = pd.read_sql_query("SELECT * FROM daily_metrics ORDER BY date ASC", conn)
if not history.empty:
    st.subheader("Weight Trend Analysis")
    st.line_chart(history.set_index('date')['weight'])
