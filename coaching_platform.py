# coaching_platform.py
# BigC's Coaching - Streamlit multi-user app with per-role dashboards and weekly check-ins
# Requirements: streamlit, pandas, matplotlib, gspread, gspread-dataframe, oauth2client, python-dateutil

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, date
import os, json
from dateutil import parser

# Optional Google Sheets support
USE_GOOGLE = True
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    from gspread_dataframe import get_as_dataframe, set_with_dataframe
except Exception:
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
        client = gspread.authorize(creds)
        return client
    if os.path.exists("service_account.json"):
        scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
        client = gspread.authorize(creds)
        return client
    raise RuntimeError("No Google credentials found.")

def ensure_sheets_structure(gc):
    sh = None
    try:
        sh = gc.open(GSHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(GSHEET_NAME)
    ws_list = {
        "coaches": ["Username","Password"],
        "clients": ["Name","AssignedCoach","Username","Password","Goal"],
        "workouts": ["ClientUsername","Workout","Details","Timestamp"],
        "nutrition": ["ClientUsername","Calories","Protein","Carbs","Fats","Timestamp"],
        "progress": ["ClientUsername","Date","Weight","Notes","Timestamp"],
        "checkins": ["ClientUsername","WeekStartDate","Feedback","Submitted","Timestamp"]
    }
    for title, headers in ws_list.items():
        try:
            ws = sh.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=title, rows=1000, cols=max(10,len(headers)))
            ws.append_row(headers)
    return sh

def read_sheet(sh, name):
    ws = sh.worksheet(name)
    df = get_as_dataframe(ws, evaluate_formulas=True, header=0, skip_blank_lines=True)
    return df.dropna(how="all")

def append_row(sh, sheet_name, row_values):
    ws = sh.worksheet(sheet_name)
    ws.append_row(row_values)

# ---------------------------
# Local fallback storage
# ---------------------------
def init_local_storage():
    for key in ["local_coaches","local_clients","local_workouts","local_nutrition","local_progress","local_checkins"]:
        if key not in st.session_state:
            st.session_state[key] = []

# ---------------------------
# Session state defaults
# ---------------------------
if "role" not in st.session_state: st.session_state.role = None
if "user" not in st.session_state: st.session_state.user = None
if "admin" not in st.session_state: st.session_state.admin = False
if "rerun_flag" not in st.session_state: st.session_state.rerun_flag = False

# ---------------------------
# Google Sheets connection
# ---------------------------
gclient = None; gsh = None; gs_ok = False; google_error = None
if USE_GOOGLE:
    try:
        gclient = gs_auth()
        gsh = ensure_sheets_structure(gclient)
        gs_ok = True
    except Exception as e:
        google_error = str(e)
if not gs_ok:
    init_local_storage()

# ---------------------------
# Header (Old UI style)
# ---------------------------
st.title(APP_TITLE)
st.markdown(f"*{APP_SUBTITLE}*")
if not gs_ok:
    st.warning("Google Sheets not connected — using local storage. Reason: "+(google_error or "unknown"))

# ---------------------------
# Sidebar Login
# ---------------------------
with st.sidebar:
    st.header("Login")
    role_choice = st.radio("Role:", ["Admin","Coach","Client"])
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")
    if st.button("Login"):
        if role_choice == "Admin":
            admin_pass = st.secrets.get(ADMIN_SECRET_KEY, DEFAULT_ADMIN_PASS) if hasattr(st, "secrets") else DEFAULT_ADMIN_PASS
            if password_input == admin_pass:
                st.session_state.role = "admin"
                st.session_state.user = "admin"
                st.session_state.admin = True
                st.success("Admin logged in")
            else:
                st.error("Wrong admin password")
        else:
            if gs_ok:
                sheet_name = "coaches" if role_choice=="Coach" else "clients"
                df = read_sheet(gsh,sheet_name)
                user_row = df[(df["Username"]==username_input)&(df["Password"]==password_input)]
                if not user_row.empty:
                    st.session_state.role = role_choice.lower()
                    st.session_state.user = username_input
                    st.success(f"{role_choice} logged in")
                else:
                    st.error("Invalid credentials")
            else:
                st.error("Google Sheets not connected; login disabled")
st.stop() if st.session_state.role is None else None

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
    def filter_df(sheet_name):
        if gs_ok:
            df = read_sheet(gsh,sheet_name)
            return df[df["ClientUsername"]==client_username].to_dict(orient="records")
        else:
            key_map = {"workouts":"local_workouts","nutrition":"local_nutrition","progress":"local_progress","checkins":"local_checkins"}
            return [r for r in st.session_state[key_map[sheet_name]] if r["ClientUsername"]==client_username]
    return {
        "workouts": filter_df("workouts"),
        "nutrition": filter_df("nutrition"),
        "progress": filter_df("progress"),
        "checkins": filter_df("checkins")
    }

# ---------------------------
# Admin Dashboard
# ---------------------------
if st.session_state.admin:
    st.header("Admin Dashboard 🔐")
    sheets = ["coaches","clients","workouts","nutrition","progress","checkins"]
    for s in sheets:
        st.subheader(s.capitalize())
        try: df = read_sheet(gsh,s)
        except: df = pd.DataFrame()
        if df.empty:
            st.info("No records")
        else:
            st.dataframe(df)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(f"Download {s}.csv", csv, file_name=f"{s}.csv", mime="text/csv")
    if st.button("Log out"):
        st.session_state.role = None
        st.session_state.user = None
        st.session_state.admin = False
        st.experimental_rerun()

# ---------------------------
# Coach Dashboard
# ---------------------------
elif st.session_state.role=="coach":
    coach_user = st.session_state.user
    st.header(f"Welcome Coach {coach_user} 👋")
    clients = get_clients_for_coach(coach_user)
    if not clients:
        st.info("No clients assigned yet")
        st.stop()
    client_names = [c["Name"] for c in clients]
    selected_client = st.selectbox("Select client", client_names)
    client_username = next(c["Username"] for c in clients if c["Name"]==selected_client)
    data = get_client_data(client_username)
    tab_w,tab_n,tab_p,tab_c = st.tabs(["🏋️ Workouts","🍎 Nutrition","📈 Progress","📋 Weekly Check-In"])

    # Workouts tab
    with tab_w:
        st.subheader("Workouts")
        with st.form("workout_form"):
            workout_name = st.text_input("Workout name")
            workout_details = st.text_area("Details")
            if st.form_submit_button("Save Workout"):
                ts = datetime.utcnow().isoformat()
                append_row(gsh,"workouts",[client_username, workout_name, workout_details, ts])
                st.success("Workout saved")
                st.session_state.rerun_flag = True

    # Nutrition tab
    with tab_n:
        st.subheader("Nutrition")
        with st.form("nutrition_form"):
            cals = st.number_input("Calories",0)
            prot = st.number_input("Protein",0)
            carbs = st.number_input("Carbs",0)
            fats = st.number_input("Fats",0)
            if st.form_submit_button("Save Nutrition"):
                ts = datetime.utcnow().isoformat()
                append_row(gsh,"nutrition",[client_username,cals,prot,carbs,fats,ts])
                st.success("Nutrition saved")
                st.session_state.rerun_flag = True

    # Progress tab
    with tab_p:
        st.subheader("Progress")
        with st.form("progress_form"):
            pdate = st.date_input("Date")
            pweight = st.number_input("Weight",0.0)
            pnotes = st.text_area("Notes")
            if st.form_submit_button("Save Progress"):
                ts = datetime.utcnow().isoformat()
                append_row(gsh,"progress",[client_username,str(pdate),pweight,pnotes,ts])
                st.success("Progress saved")
                st.session_state.rerun_flag = True

    # Weekly Check-In tab
    with tab_c:
        st.subheader("Weekly Check-In")
        if data["checkins"]:
            st.dataframe(pd.DataFrame(data["checkins"]))

# ---------------------------
# Client Dashboard
# ---------------------------
elif st.session_state.role=="client":
    client_user = st.session_state.user
    st.header(f"Welcome {client_user} 👋")
    data = get_client_data(client_user)
    tab_w,tab_n,tab_p,tab_c = st.tabs(["🏋️ Workouts","🍎 Nutrition","📈 Progress","📋 Weekly Check-In"])

    with tab_w:
        st.subheader("Workouts")
        if data["workouts"]:
            st.dataframe(pd.DataFrame(data["workouts"]))
        else: st.info("No workouts yet")

    with tab_n:
        st.subheader("Nutrition")
        if data["nutrition"]:
            st.dataframe(pd.DataFrame(data["nutrition"]))
        else: st.info("No nutrition logged yet")

    with tab_p:
        st.subheader("Progress")
        if data["progress"]:
            pdf = pd.DataFrame(data["progress"])
            st.dataframe(pdf)
            if "Weight" in pdf.columns and "Date" in pdf.columns:
                try: st.line_chart(pdf.set_index("Date")["Weight"])
                except: pass
        else: st.info("No progress logged yet")

    with tab_c:
        st.subheader("Weekly Check-In")
        with st.form("client_checkin_form"):
            week_start = st.date_input("Week Starting")
            feedback = st.text_area("Your weekly feedback / notes")
            if st.form_submit_button("Submit Check-In"):
                ts = datetime.utcnow().isoformat()
                append_row(gsh,"checkins",[client_user,str(week_start),feedback,"Submitted",ts])
                st.success("Check-in submitted!")
                st.session_state.rerun_flag = True
        if data["checkins"]:
            st.dataframe(pd.DataFrame(data["checkins"]))

# ---------------------------
# Handle safe rerun
# ---------------------------
if st.session_state.get("rerun_flag"):
    st.session_state.rerun_flag = False
    st.experimental_rerun()
