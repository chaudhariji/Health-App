import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

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

# --- DATA RETRIEVAL & CALCULATIONS ---
today = datetime.now().strftime('%Y-%m-%d')
all_history = pd.read_sql_query("SELECT * FROM daily_metrics ORDER BY date ASC", conn)

# Calculate Weight Change (Compared to previous entry)
if len(all_history) >= 2:
    weight_change = all_history['weight'].iloc[-1] - all_history['weight'].iloc[-2]
else:
    weight_change = 0.0

current_weight = all_history['weight'].iloc[-1] if not all_history.empty else 175.0
protein_target = int(current_weight)

# --- HEADER & INPUT BUTTON ---
head_col, btn_col = st.columns([5, 1])

with head_col:
    st.title("Today’s health summary")

@st.dialog("Log Daily Metrics")
def input_dialog():
    with st.form("Daily Totals", clear_on_submit=True):
        w = st.number_input("Current Weight (lbs)", value=current_weight, step=0.1)
        c_in = st.number_input("Calories Consumed", min_value=0)
        c_out = st.number_input("Calories Burnt", min_value=0)
        p = st.number_input("Protein (g)", min_value=0)
        f = st.number_input("Fiber (g)", min_value=0)
        w_l = st.number_input("Water (L)", min_value=0.0, step=0.5)
        
        if st.form_submit_button("Save Data"):
            conn.execute("""INSERT INTO daily_metrics VALUES (?, ?, ?, ?, ?, ?, ?) 
                         ON CONFLICT(date) DO UPDATE SET 
                         weight=excluded.weight, calories_in=excluded.calories_in, 
                         protein=excluded.protein, fiber=excluded.fiber, 
                         water=excluded.water, calories_burnt=excluded.calories_burnt""", 
                         (today, w, c_in, p, f, w_l, c_out))
            conn.commit()
            st.rerun()

with btn_col:
    st.write("") # Spacing to align with title
    if st.button("**+**", help="Add Entry", use_container_width=True):
        input_dialog()

# --- METRIC DASHBOARD ---
today_data = all_history[all_history['date'] == today]

if not today_data.empty:
    row = today_data.iloc[0]
    net_cals = row['calories_in'] - row['calories_burnt']
    
    # Layout 1: Weight Change & Net Calories Side-by-Side
    c1, c2 = st.columns(2)
    c1.metric("Net Weight Change", f"{weight_change:+.1f} lbs")
    c2.metric("Net Calories", f"{net_cals} kcal", f"In: {row['calories_in']} | Out: {row['calories_burnt']}")

    st.divider()

    # Layout 2: Macros & Hydration Side-by-Side
    c3, c4, c5 = st.columns(3)
    c3.metric("Protein Intake", f"{row['protein']}g", f"Target: {protein_target}g")
    c4.metric("Fiber Intake", f"{row['fiber']}g", "Goal: 30g")
    c5.metric("Water Intake", f"{row['water']}L", "Goal: 3.7L")
else:
    st.info("Log your metrics using the **+** button in the top right.")

st.divider()

# --- WEIGHT ANALYTICS & CUSTOM DATE RANGE ---
st.subheader("Weight Trend Analysis")

if not all_history.empty:
    # Date Range Selectors
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
    with col_date2:
        end_date = st.date_input("End Date", datetime.now())

    # Filtering Logic
    mask = (pd.to_datetime(all_history['date']).dt.date >= start_date) & \
           (pd.to_datetime(all_history['date']).dt.date <= end_date)
    filtered_df = all_history.loc[mask]

    if not filtered_df.empty:
        # Absolute Change calculation
        abs_change = filtered_df['weight'].iloc[-1] - filtered_df['weight'].iloc[0]
        st.write(f"### Total Period Change: **{abs_change:+.1f} lbs**")
        
        # Line chart for the specific range
        chart_data = filtered_df.set_index('date')['weight']
        st.line_chart(chart_data)
    else:
        st.warning("No data found for the selected range.")
