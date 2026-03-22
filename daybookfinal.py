
import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from fpdf import FPDF
from datetime import datetime, timedelta
from streamlit_option_menu import option_menu

# --- PAGE CONFIG ---
st.set_page_config(page_title="CloudBooks Enterprise", layout="wide", page_icon="🔐")

# --- DATABASE & SECURITY ---
conn = sqlite3.connect('cloudbooks_enterprise_v2.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, date TEXT, type TEXT, description TEXT, amount REAL, person TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    conn.commit()
    
    # Default Users if not exist
    c.execute("SELECT * FROM users")
    if not c.fetchone():
        admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
        staff_pw = hashlib.sha256("staff123".encode()).hexdigest()
        c.execute("INSERT INTO users VALUES (?,?,?)", ("admin", admin_pw, "Admin"))
        c.execute("INSERT INTO users VALUES (?,?,?)", ("staff", staff_pw, "Staff"))
        conn.commit()

init_db()

# --- CSS STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    [data-testid="stSidebar"] { background-color: #2c3e50; }
    .status-card { background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 4px solid #2ca01c; text-align: center; }
    .metric-val { font-size: 22px; font-weight: bold; color: #333; }
    .metric-label { font-size: 12px; color: #666; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False
    st.session_state['user'] = None
    st.session_state['role'] = None

# --- LOGIN UI ---
if not st.session_state['auth']:
    st.markdown("<h2 style='text-align:center;'>🏢 CloudBooks Login</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type='password')
            if st.form_submit_button("Login"):
                hashed_p = hashlib.sha256(p.encode()).hexdigest()
                c.execute("SELECT role FROM users WHERE username=? AND password=?", (u, hashed_p))
                res = c.fetchone()
                if res:
                    st.session_state['auth'] = True
                    st.session_state['user'] = u
                    st.session_state['role'] = res[0]
                    st.rerun()
                else:
                    st.error("Invalid Username/Password")
else:
    # --- AUTHENTICATED PANEL ---
    with st.sidebar:
        st.markdown(f"<h3 style='color:white;'>Welcome, {st.session_state['user']}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#2ca01c;'>Role: {st.session_state['role']}</p>", unsafe_allow_html=True)
        st.divider()
        
        # Menu Filter based on Role
        if st.session_state['role'] == "Admin":
            options = ["Dashboard", "Banking (Entries)", "Sales & Expenses", "Reports", "User Settings", "Logout"]
            icons = ["speedometer2", "bank", "receipt", "file-earmark-text", "gear", "box-arrow-right"]
        else:
            options = ["Banking (Entries)", "Logout"]
            icons = ["bank", "box-arrow-right"]
            
        selected = option_menu(None, options, icons=icons, menu_icon="cast", default_index=0,
            styles={"nav-link-selected": {"background-color": "#2ca01c"}})

    if selected == "Logout":
        st.session_state['auth'] = False
        st.rerun()

    # --- ADMIN DASHBOARD ---
    if selected == "Dashboard":
        st.markdown("## Business Dashboard")
        df = pd.read_sql_query("SELECT * FROM transactions", conn)
        total_in = df[df['type'] == 'Receipt']['amount'].sum()
        total_out = df[df['type'] == 'Expense']['amount'].sum()
        bal = total_in - total_out
        
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='status-card'><div class='metric-label'>Total Income</div><div class='metric-val'>Rs. {total_in:,.0f}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='status-card' style='border-top-color:red'><div class='metric-label'>Total Expenses</div><div class='metric-val'>Rs. {total_out:,.0f}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='status-card' style='border-top-color:blue'><div class='metric-label'>Net Balance</div><div class='metric-val'>Rs. {bal:,.0f}</div></div>", unsafe_allow_html=True)
        
        st.divider()
        st.subheader("Transaction History")
        st.dataframe(df.tail(10), use_container_width=True)

    # --- BANKING / ENTRIES (Both can access) ---
    elif selected == "Banking (Entries)":
        st.markdown("## 📥 Add Transaction")
        with st.form("entry"):
            date = st.date_input("Date")
            t_type = st.selectbox("Type", ["Receipt", "Expense", "Dasti Advance"])
            amount = st.number_input("Amount (PKR)", min_value=0.0)
            desc = st.text_input("Memo")
            if st.form_submit_button("Save Record"):
                c.execute("INSERT INTO transactions (date, type, description, amount) VALUES (?,?,?,?)",
                          (date.strftime("%Y-%m-%d"), t_type, desc, amount))
                conn.commit()
                st.success("Saved!")

    # --- REPORTS (Admin Only) ---
    elif selected == "Reports":
        st.markdown("## 📊 Financial Reports")
        df_rep = pd.read_sql_query("SELECT * FROM transactions", conn)
        st.dataframe(df_rep, use_container_width=True)
        csv = df_rep.to_csv(index=False).encode('utf-8')
        st.download_button("Export to Excel", csv, "report.csv", "text/csv")

    # --- USER SETTINGS (Admin Only) ---
    elif selected == "User Settings":
        st.subheader("Manage Users")
        new_u = st.text_input("New Username")
        new_p = st.text_input("New Password", type='password')
        new_r = st.selectbox("Role", ["Admin", "Staff"])
        if st.button("Create User"):
            hp = hashlib.sha256(new_p.encode()).hexdigest()
            try:
                c.execute("INSERT INTO users VALUES (?,?,?)", (new_u, hp, new_r))
                conn.commit()
                st.success("User Created!")
            except:
                st.error("User already exists!")
