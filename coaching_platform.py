# ultimate_coaching_dashboard.py
# BigC's Coaching - Complete web-based dashboard with filters, client creation, self-signup
# Packages: streamlit, pandas, matplotlib, gspread, gspread-dataframe, oauth2client, python-dateutil

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, date, timedelta
import os, json
from dateutil import parser

# Google Sheets support
USE_GOOGLE = True
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    from gspread_dataframe import get_as_dataframe, set_with_dataframe
except:
    USE_GOOGLE = False

# ---------------------------
# Configuration
# ---------------------------
APP_TITLE = "BigC's Coaching"
APP_SUBTITLE = "@callumjules"
DEFAULT_ADMIN_PASS = "bigc_admin_pass"
ADMIN_SECRET_KEY = "ADMIN_PASS"
GSHEET_NAME = "BigC Coaching Data"

st.set_page_config(page_title=APP_TITLE, page_icon="💪", layout="wide")

# ---------------------------
# Google Sheets Helpers
# ---------------------------
def gs_auth():
    if not USE_GOOGLE:
        raise RuntimeError("gspread or oauth2client not installed.")
    if "gcp_service_account" in st.secrets:
        raw = st.secrets["gcp_service_account"]
        creds_json = json.loads(raw)
        scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        return gspread.authorize(creds)
    if os.path.exists("service_account.json"):
        scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
        return gspread.authorize(creds)
    raise RuntimeError("No Google credentials found.")

def ensure_sheets(gc):
    sh = None
    try:
        sh = gc.open(GSHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(GSHEET_NAME)
    sheets = {
        "coaches":["Username","Password"],
        "clients":["Name","AssignedCoach","Username","Password","Goal"],
        "workouts":["ClientUsername","Workout","Details","Timestamp"],
        "nutrition":["ClientUsername","Calories","Protein","Carbs","Fats","Timestamp"],
        "progress":["ClientUsername","Date","Weight","Notes","Timestamp"],
        "checkins":["ClientUsername","WeekStartDate","Feedback","Submitted","Timestamp"]
    }
    for title, headers in sheets.items():
        try:
            ws = sh.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=title, rows=1000, cols=max(10,len(headers)))
            ws.append_row(headers)
    return sh

def read_sheet(sh, sheet_name):
    ws = sh.worksheet(sheet_name)
    df = get_as_dataframe(ws, evaluate_formulas=True, header=0, skip_blank_lines=True)
    return df.dropna(how="all")

def append_row(sh, sheet_name, row_values):
    ws = sh.worksheet(sheet_name)
    ws.append_row(row_values)

# ---------------------------
# Local storage fallback
# ---------------------------
def init_local_storage():
    for key in ["local_coaches","local_clients","local_workouts","local_nutrition","local_progress","local_checkins"]:
        if key not in st.session_state:
            st.session_state[key] = []

# ---------------------------
# Session state defaults
# ---------------------------
for key in ["role","user","admin","rerun_flag"]:
    if key not in st.session_state:
        st.session_state[key] = None if key!="rerun_flag" else False

# ---------------------------
# Connect to Google Sheets
# ---------------------------
gclient = None; gsh = None; gs_ok = False; google_error = None
if USE_GOOGLE:
    try:
        gclient = gs_auth()
        gsh = ensure_sheets(gclient)
        gs_ok = True
    except Exception as e:
        google_error = str(e)
if not gs_ok:
    init_local_storage()

# ---------------------------
# Header
# ---------------------------
st.title(APP_TITLE)
st.markdown(f"*{APP_SUBTITLE}*")
if not gs_ok:
    st.warning(f"Google Sheets not connected — using local storage. Reason: {google_error or 'unknown'}")

# ---------------------------
# Client Signup (if not logged in)
# ---------------------------
if st.session_state.role is None:
    st.sidebar.subheader("New Client Signup")
    signup_name = st.sidebar.text_input("Full Name", key="signup_name")
    signup_username = st.sidebar.text_input("Username", key="signup_username")
    signup_password = st.sidebar.text_input("Password", type="password", key="signup_password")
    signup_goal = st.sidebar.text_input("Goal / Focus", key="signup_goal")
    
    # Checklist
    st.sidebar.markdown("**Pre-Signup Checklist**")
    c1 = st.sidebar.checkbox("I have completed a health assessment", key="signup_c1")
    c2 = st.sidebar.checkbox("I have no injuries preventing training", key="signup_c2")
    c3 = st.sidebar.checkbox("I agree to the coaching terms", key="signup_c3")

    # Assign coach
    if gs_ok:
        try:
            coaches_df = read_sheet(gsh,"coaches")
            coach_list = list(coaches_df["Username"].unique())
        except:
            coach_list = ["coach1"]
    else:
        coach_list = [c["Username"] for c in st.session_state.local_coaches] or ["coach1"]
    signup_coach = st.sidebar.selectbox("Select your coach", coach_list, key="signup_coach")

    if st.sidebar.button("Sign Up", key="signup_submit"):
        if not (signup_name and signup_username and signup_password):
            st.sidebar.warning("Please fill in all fields")
        elif not (c1 and c2 and c3):
            st.sidebar.warning("Please complete the checklist")
        else:
            row = [signup_name, signup_coach, signup_username, signup_password, signup_goal]
            if gs_ok:
                append_row(gsh,"clients",row)
            else:
                st.session_state.local_clients.append({
                    "Name":signup_name,
                    "AssignedCoach":signup_coach,
                    "Username":signup_username,
                    "Password":signup_password,
                    "Goal":signup_goal
                })
            st.sidebar.success(f"Client {signup_name} registered! You can now log in.")

# ---------------------------
# Sidebar Login
# ---------------------------
with st.sidebar:
    st.header("Login")
    role_choice = st.radio("Role:", ["Admin","Coach","Client"], key="login_role")
    username_input = st.text_input("Username", key="login_username")
    password_input = st.text_input("Password", type="password", key="login_password")
    if st.button("Login", key="login_submit"):
        if role_choice=="Admin":
            admin_pass = st.secrets.get("ADMIN_PASS", "bigc_admin_pass") if hasattr(st, "secrets") else "bigc_admin_pass"
            if password_input==admin_pass:
                st.session_state.role="admin"
                st.session_state.user="admin"
                st.session_state.admin=True
                st.success("Admin logged in")
            else: st.error("Wrong admin password")
        else:
            # fallback local users
            if gs_ok:
                sheet_name = "coaches" if role_choice=="Coach" else "clients"
                df = read_sheet(gsh, sheet_name)
            else:
                if role_choice=="Coach":
                    df = pd.DataFrame([{"Username":"coach1","Password":"pass"}])
                else:
                    df = pd.DataFrame([{"Username":"client1","Password":"pass","AssignedCoach":"coach1"}])
            user_row = df[(df["Username"]==username_input)&(df["Password"]==password_input)]
            if not user_row.empty:
                st.session_state.role = role_choice.lower()
                st.session_state.user = username_input
                st.success(f"{role_choice} logged in")
            else:
                st.error("Invalid credentials")

st.write("Current role:", st.session_state.role)
st.write("Current user:", st.session_state.user)

# ---------------------------
# Data helpers
# ---------------------------
def get_clients_for_coach(coach_username):
    if gs_ok:
        df = read_sheet(gsh,"clients")
        return df[df["AssignedCoach"]==coach_username].to_dict(orient="records")
    else:
        return [c for c in st.session_state.local_clients if c.get("AssignedCoach")==coach_username]

def get_client_data(client_username):
    key_map = {"workouts":"local_workouts","nutrition":"local_nutrition","progress":"local_progress","checkins":"local_checkins"}
    def filter_df(sheet_name):
        if gs_ok:
            df = read_sheet(gsh, sheet_name)
            return df[df["ClientUsername"]==client_username].to_dict(orient="records")
        else:
            return [r for r in st.session_state[key_map[sheet_name]] if r["ClientUsername"]==client_username]
    return {
        "workouts": filter_df("workouts"),
        "nutrition": filter_df("nutrition"),
        "progress": filter_df("progress"),
        "checkins": filter_df("checkins")
    }

# ---------------------------
# Safe rerun helper
# ---------------------------
def safe_rerun():
    st.session_state.rerun_flag = False
    st.experimental_rerun()

if st.session_state.rerun_flag:
    safe_rerun()

# ---------------------------
# Filter function
# ---------------------------
def apply_filters(entries, start_date=None, end_date=None, workout=None):
    filtered = []
    for e in entries:
        ts = e.get("Timestamp") or e.get("Date") or e.get("WeekStartDate")
        if ts:
            try:
                e_date = parser.parse(ts).date()
                if start_date and e_date < start_date:
                    continue
                if end_date and e_date > end_date:
                    continue
            except:
                pass
        if workout and e.get("Workout") and workout!="All" and e.get("Workout")!=workout:
            continue
        filtered.append(e)
    return filtered
