import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('fitness_data.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS daily_metrics 
                 (date TEXT UNIQUE, weight FLOAT, calories_in INTEGER, 
                  protein INTEGER, fiber INTEGER, water FLOAT, calories_burnt INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS fasting_logs 
                 (start_time TEXT, end_time TEXT, duration_hours FLOAT)''')
    conn.commit()
    return conn

conn = init_db()

# --- APP UI CONFIG ---
st.set_page_config(page_title="WIW Performance", layout="wide")
st.title("🛡️ WIW Health Dashboard")

# --- DATA & GOALS ---
today = datetime.now().strftime('%Y-%m-%d')
latest_data = pd.read_sql_query("SELECT weight FROM daily_metrics ORDER BY date DESC LIMIT 1", conn)
current_weight = latest_data['weight'].iloc[0] if not latest_data.empty else 175.0
protein_target = int(current_weight)

# --- THE INPUT BUTTON (MODAL) ---
@st.dialog("Log Your Daily Metrics")
def input_dialog():
    with st.form("Daily Totals", clear_on_submit=True):
        w = st.number_input("Current Weight (lbs)", value=current_weight, step=0.1)
        c_in = st.number_input("Calories Consumed", min_value=0)
        c_out = st.number_input("Calories Burnt (Exercise)", min_value=0)
        p = st.number_input("Protein (g)", min_value=0)
        f = st.number_input("Fiber (g)", min_value=0)
        w_liters = st.number_input("Water (L)", min_value=0.0, step=0.5)
        
        if st.form_submit_button("Save & Update Dashboard"):
            conn.execute("""INSERT INTO daily_metrics (date, weight, calories_in, protein, fiber, water, calories_burnt) 
                         VALUES (?, ?, ?, ?, ?, ?, ?) 
                         ON CONFLICT(date) DO UPDATE SET 
                         weight=excluded.weight, calories_in=excluded.calories_in, 
                         protein=excluded.protein, fiber=excluded.fiber, 
                         water=excluded.water, calories_burnt=excluded.calories_burnt""", 
                         (today, w, c_in, p, f, w_liters, c_out))
            conn.commit()
            st.rerun()

# --- HOME SCREEN LAYOUT ---
col_btn, col_empty = st.columns([1, 3])
with col_btn:
    if st.button("➕ Input Today's Data", use_container_width=True):
        input_dialog()

st.divider()

# --- DASHBOARD VISUALS ---
df = pd.read_sql_query(f"SELECT * FROM daily_metrics WHERE date='{today}'", conn)
fast_df = pd.read_sql_query(f"SELECT SUM(duration_hours) as total FROM fasting_logs WHERE start_time LIKE '{today}%'", conn)

if not df.empty:
    row = df.iloc[0]
    net_cals = row['calories_in'] - row['calories_burnt']
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Net Calories", f"{net_cals} kcal", f"In: {row['calories_in']}")
    m2.metric("Protein Intake", f"{row['protein']}g", f"Target: {protein_target}g")
    m3.metric("Fasted Today", f"{round(fast_df['total'].iloc[0] or 0, 1)} hrs")
    
    m4, m5, m6 = st.columns(3)
    m4.metric("Fiber", f"{row['fiber']}g", "Goal: 30g")
    m5.metric("Water", f"{row['water']}L", "Goal: 3.7L")
    m6.metric("Current Weight", f"{row['weight']} lbs")
else:
    st.info("No data logged for today yet. Click the 'Input' button above to start!")

# --- FASTING TIMER (SIDEBAR) ---
with st.sidebar:
    st.header("⏳ Fasting")
    if 'fasting' not in st.session_state:
        st.session_state.fasting = False

    if not st.session_state.fasting:
        if st.button("Start Fast"):
            st.session_state.start_time = datetime.now()
            st.session_state.fasting = True
            st.rerun()
    else:
        elapsed = (datetime.now() - st.session_state.start_time).total_seconds() / 3600
        st.write(f"Running: **{elapsed:.2f} hrs**")
        if st.button("Stop Fast"):
            conn.execute("INSERT INTO fasting_logs VALUES (?, ?, ?)", 
                         (st.session_state.start_time, datetime.now(), round(elapsed, 2)))
            conn.commit()
            st.session_state.fasting = False
            st.rerun()
