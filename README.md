import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('fitness_data.db')
    c = conn.cursor()
    # Unified table for weight, nutrition, and activity
    c.execute('''CREATE TABLE IF NOT EXISTS daily_metrics 
                 (date TEXT UNIQUE, weight FLOAT, calories_in INTEGER, 
                  protein INTEGER, fiber INTEGER, water FLOAT, calories_burnt INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS fasting_logs 
                 (start_time TEXT, end_time TEXT, duration_hours FLOAT)''')
    conn.commit()
    return conn

conn = init_db()

# --- APP UI ---
st.set_page_config(page_title="Elite Performance Tracker", layout="wide")
st.title("⚡ Performance & Metabolic Dashboard")

# --- DATA RETRIEVAL ---
latest_data = pd.read_sql_query("SELECT weight FROM daily_metrics ORDER BY date DESC LIMIT 1", conn)
current_weight = latest_data['weight'].iloc[0] if not latest_data.empty else 175.0
protein_target = int(current_weight) 

# --- SIDEBAR: FASTING & WEIGHT ---
with st.sidebar:
    st.header("🏃 Management")
    
    # Weight & Fasting logic remains persistent
    new_weight = st.number_input("Current Weight (lbs)", value=current_weight, step=0.1)
    
    st.divider()
    st.subheader("⏳ Fasting Timer")
    if 'fasting' not in st.session_state:
        st.session_state.fasting = False

    if not st.session_state.fasting:
        if st.button("Start Fast"):
            st.session_state.start_time = datetime.now()
            st.session_state.fasting = True
    else:
        elapsed = (datetime.now() - st.session_state.start_time).total_seconds() / 3600
        st.write(f"Fasting: {elapsed:.2f} hrs")
        if st.button("End Fast"):
            duration = round(elapsed, 2)
            conn.execute("INSERT INTO fasting_logs VALUES (?, ?, ?)", 
                         (st.session_state.start_time, datetime.now(), duration))
            conn.commit()
            st.session_state.fasting = False
            st.rerun()

# --- MAIN DASHBOARD: INPUT & ANALYTICS ---
today = datetime.now().strftime('%Y-%m-%d')
col_input, col_dash = st.columns([1, 2])

with col_input:
    st.subheader("Log Daily Data")
    with st.form("Daily Totals"):
        c_in = st.number_input("Calories Consumed", min_value=0)
        c_out = st.number_input("Calories Burnt (Exercise)", min_value=0)
        p = st.number_input("Protein (g)", min_value=0)
        f = st.number_input("Fiber (g)", min_value=0)
        w = st.number_input("Water (L)", min_value=0.0)
        
        if st.form_submit_button("Update Dashboard"):
            conn.execute("""INSERT INTO daily_metrics (date, weight, calories_in, protein, fiber, water, calories_burnt) 
                         VALUES (?, ?, ?, ?, ?, ?, ?) 
                         ON CONFLICT(date) DO UPDATE SET 
                         weight=excluded.weight, calories_in=excluded.calories_in, 
                         protein=excluded.protein, fiber=excluded.fiber, 
                         water=excluded.water, calories_burnt=excluded.calories_burnt""", 
                         (today, new_weight, c_in, p, f, w, c_out))
            conn.commit()
            st.success("Data Saved!")

with col_dash:
    st.subheader(f"Status: {today}")
    df = pd.read_sql_query(f"SELECT * FROM daily_metrics WHERE date='{today}'", conn)
    
    if not df.empty:
        row = df.iloc[0]
        net_cals = row['calories_in'] - row['calories_burnt']
        
        # Row 1: The Core Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Net Calories", f"{net_cals} kcal", f"In: {row['calories_in']}")
        m2.metric("Protein", f"{row['protein']}g", f"Target: {protein_target}g")
        m3.metric("Calories Burnt", f"{row['calories_burnt']} kcal", delta_color="normal")
        
        # Row 2: Health Metrics
        m4, m5, m6 = st.columns(3)
        m4.metric("Fiber", f"{row['fiber']}g", "Goal: 30g")
        m5.metric("Water", f"{row['water']}L", "Goal: 3.7L")
        m6.metric("Weight", f"{row['weight']} lbs")

# --- TREND ANALYSIS ---
st.divider()
st.subheader("Weekly Activity vs. Intake")
history = pd.read_sql_query("SELECT date, calories_in, calories_burnt FROM daily_metrics", conn)
if not history.empty:
    st.area_chart(history.set_index('date'))
