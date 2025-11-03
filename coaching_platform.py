# ultimate_coaching_dashboard.py
# BigC's Coaching Dashboard - Streamlit Cloud Ready

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, date, timedelta
import json, os

# ---------------------------
# Configuration
# ---------------------------
APP_TITLE = "BigC's Coaching"
APP_SUBTITLE = "@callumjules"
DEFAULT_ADMIN_PASS = "bigc_admin_pass"
GSHEET_NAME = "BigC Coaching Data"
st.set_page_config(page_title=APP_TITLE, page_icon="💪", layout="wide")

# ---------------------------
# Google Sheets Authentication
# ---------------------------
USE_GOOGLE = "gcp_service_account" in st.secrets

if USE_GOOGLE:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    from gspread_dataframe import get_as_dataframe, set_with_dataframe

    def gs_auth():
        raw = st.secrets["gcp_service_account"]
        creds_json = json.loads(raw)
        scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        return gspread.authorize(creds)
    
    gclient = gs_auth()

    def ensure_sheets():
        try:
            sh = gclient.open(GSHEET_NAME)
        except gspread.SpreadsheetNotFound:
            sh = gclient.create(GSHEET_NAME)
        sheets = {
            "coaches":["Username","Password","ProfilePic"],
            "clients":["Name","AssignedCoach","Username","Password","Goal","ProfilePic"],
            "workouts":["ClientUsername","Workout","Details","Timestamp","ImageURL"],
            "nutrition":["ClientUsername","Calories","Protein","Carbs","Fats","Timestamp"],
            "progress":["ClientUsername","Date","Weight","Notes","Timestamp","ImageURL"],
            "checkins":["ClientUsername","WeekStartDate","Feedback","Submitted","Timestamp","ImageURL"]
        }
        for title, headers in sheets.items():
            try:
                ws = sh.worksheet(title)
            except gspread.WorksheetNotFound:
                ws = sh.add_worksheet(title=title, rows=1000, cols=max(10,len(headers)))
                ws.append_row(headers)
        return sh
    
    gsh = ensure_sheets()

    def read_sheet(sheet_name):
        ws = gsh.worksheet(sheet_name)
        df = get_as_dataframe(ws, evaluate_formulas=True, header=0, skip_blank_lines=True)
        return df.fillna("")

    def append_row(sheet_name, row_values):
        ws = gsh.worksheet(sheet_name)
        ws.append_row(row_values)
else:
    # Local fallback
    for key in ["coaches","clients","workouts","nutrition","progress","checkins"]:
        if key not in st.session_state:
            st.session_state[key] = []

# ---------------------------
# Session defaults
# ---------------------------
for key in ["role","user","admin","rerun_flag"]:
    if key not in st.session_state:
        st.session_state[key] = None if key!="rerun_flag" else False

# ---------------------------
# Header
# ---------------------------
st.markdown(f"<h1 style='color:red'>{APP_TITLE}</h1>", unsafe_allow_html=True)
st.markdown(f"<h4 style='color:white'>{APP_SUBTITLE}</h4>", unsafe_allow_html=True)
if USE_GOOGLE:
    st.success("Google Sheets connected!")
else:
    st.warning("Using local storage. Google Sheets not connected.")

# ---------------------------
# Helper functions
# ---------------------------
def get_clients_for_coach(coach_username):
    if USE_GOOGLE:
        df = read_sheet("clients")
        return df[df["AssignedCoach"]==coach_username].to_dict(orient="records")
    else:
        return [c for c in st.session_state["clients"] if c.get("AssignedCoach")==coach_username]

def get_client_data(client_username):
    key_map = ["workouts","nutrition","progress","checkins"]
    data = {}
    for k in key_map:
        if USE_GOOGLE:
            df = read_sheet(k)
            data[k] = df[df["ClientUsername"]==client_username].to_dict(orient="records")
        else:
            data[k] = [r for r in st.session_state[k] if r["ClientUsername"]==client_username]
    return data

def safe_rerun():
    st.session_state.rerun_flag=False
    st.experimental_rerun()

def apply_filters(entries, start_date=None, end_date=None, workout=None):
    filtered = []
    for e in entries:
        ts = e.get("Timestamp") or e.get("Date") or e.get("WeekStartDate")
        if ts:
            try:
                e_date = datetime.strptime(ts[:10],"%Y-%m-%d").date()
                if start_date and e_date<start_date: continue
                if end_date and e_date>end_date: continue
            except: pass
        if workout and e.get("Workout") and workout!="All" and e.get("Workout")!=workout: continue
        filtered.append(e)
    return filtered

# ---------------------------
# Client Signup
# ---------------------------
if st.session_state.role is None:
    st.sidebar.subheader("New Client Signup")
    signup_name = st.sidebar.text_input("Full Name")
    signup_username = st.sidebar.text_input("Username")
    signup_password = st.sidebar.text_input("Password", type="password")
    signup_goal = st.sidebar.text_input("Goal / Focus")
    st.sidebar.markdown("**Checklist**")
    c1 = st.sidebar.checkbox("I have completed a health assessment")
    c2 = st.sidebar.checkbox("I have no injuries")
    c3 = st.sidebar.checkbox("I agree to coaching terms")

    # Coach selection
    if USE_GOOGLE:
        try:
            coaches_df = read_sheet("coaches")
            coach_list = list(coaches_df["Username"])
        except:
            coach_list = ["coach1"]
    else:
        coach_list = [c["Username"] for c in st.session_state["coaches"]] or ["coach1"]

    signup_coach = st.sidebar.selectbox("Select your coach", coach_list)

    if st.sidebar.button("Sign Up"):
        if not (signup_name and signup_username and signup_password):
            st.sidebar.warning("Fill all fields")
        elif not (c1 and c2 and c3):
            st.sidebar.warning("Complete the checklist")
        else:
            row = [signup_name, signup_coach, signup_username, signup_password, signup_goal, ""]
            if USE_GOOGLE:
                append_row("clients", row)
            else:
                st.session_state["clients"].append(dict(
                    Name=signup_name, AssignedCoach=signup_coach, Username=signup_username,
                    Password=signup_password, Goal=signup_goal, ProfilePic=""
                ))
            st.sidebar.success(f"Client {signup_name} registered! You can now log in.")

# ---------------------------
# Sidebar Login
# ---------------------------
with st.sidebar:
    st.header("Login")
    role_choice = st.radio("Role:", ["Admin","Coach","Client"])
    username_input = st.text_input("Username", key=f"{role_choice}_user")
    password_input = st.text_input("Password", type="password", key=f"{role_choice}_pass")
    if st.button("Login"):
        if role_choice=="Admin":
            admin_pass = DEFAULT_ADMIN_PASS
            if password_input==admin_pass:
                st.session_state.role="admin"
                st.session_state.user="admin"
                st.session_state.admin=True
                st.success("Admin logged in")
            else: st.error("Wrong admin password")
        else:
            sheet_name = "coaches" if role_choice=="Coach" else "clients"
            if USE_GOOGLE:
                df = read_sheet(sheet_name)
            else:
                df = pd.DataFrame(st.session_state[sheet_name])
            user_row = df[(df["Username"]==username_input)&(df["Password"]==password_input)]
            if not user_row.empty:
                st.session_state.role = role_choice.lower()
                st.session_state.user = username_input
                st.success(f"{role_choice} logged in")
            else:
                st.error("Invalid credentials")

# ---------------------------
# Admin Dashboard
# ---------------------------
if st.session_state.role=="admin":
    st.header("Admin Dashboard")
    tabs = st.tabs(["Coaches","Clients","Workouts","Nutrition","Progress","Check-Ins"])
    for tab, sheet in zip(tabs, ["coaches","clients","workouts","nutrition","progress","checkins"]):
        with tab:
            if USE_GOOGLE:
                df = read_sheet(sheet)
            else:
                df = pd.DataFrame(st.session_state[sheet])
            st.dataframe(df)
            if st.button(f"Export {sheet} CSV"):
                df.to_csv(f"{sheet}.csv", index=False)
                st.success(f"{sheet}.csv saved locally")

# ---------------------------
# Coach Dashboard
# ---------------------------
elif st.session_state.role=="coach":
    coach_user = st.session_state.user
    st.header(f"Coach Dashboard: {coach_user}")

    clients = get_clients_for_coach(coach_user)
    client_usernames = [c["Username"] for c in clients]
    if client_usernames:
        selected_client = st.selectbox("Select Client", client_usernames)
        data = get_client_data(selected_client)

        # Tabs
        tab_w, tab_n, tab_p, tab_c = st.tabs(["🏋️ Workouts","🍎 Nutrition","📈 Progress","📋 Weekly Check-In"])

        with tab_w:
            st.subheader("Workouts")
            filtered = apply_filters(data["workouts"])
            if filtered: st.dataframe(pd.DataFrame(filtered))
            else: st.info("No workouts")

        with tab_n:
            st.subheader("Nutrition")
            filtered = apply_filters(data["nutrition"])
            if filtered: st.dataframe(pd.DataFrame(filtered))
            else: st.info("No nutrition")

        with tab_p:
            st.subheader("Progress")
            filtered = apply_filters(data["progress"])
            if filtered:
                df_prog = pd.DataFrame(filtered)
                st.dataframe(df_prog)
                if "Weight" in df_prog.columns and "Date" in df_prog.columns:
                    try: st.line_chart(df_prog.set_index("Date")["Weight"])
                    except: pass
            else: st.info("No progress")

        with tab_c:
            st.subheader("Weekly Check-In")
            filtered = apply_filters(data["checkins"])
            if filtered: st.dataframe(pd.DataFrame(filtered))
            else: st.info("No check-ins")

# ---------------------------
# Client Dashboard
# ---------------------------
elif st.session_state.role=="client":
    client_user = st.session_state.user
    st.header(f"Welcome {client_user} 👋")
    data = get_client_data(client_user)

    tab_w, tab_n, tab_p, tab_c = st.tabs(["🏋️ Workouts","🍎 Nutrition","📈 Progress","📋 Weekly Check-In"])
    with tab_w:
        st.subheader("Workouts")
        filtered = apply_filters(data["workouts"])
        if filtered: st.dataframe(pd.DataFrame(filtered))
        else: st.info("No workouts")

    with tab_n:
        st.subheader("Nutrition")
        filtered = apply_filters(data["nutrition"])
        if filtered: st.dataframe(pd.DataFrame(filtered))
        else: st.info("No nutrition")

    with tab_p:
        st.subheader("Progress")
        filtered = apply_filters(data["progress"])
        if filtered:
            df_prog = pd.DataFrame(filtered)
            st.dataframe(df_prog)
            if "Weight" in df_prog.columns and "Date" in df_prog.columns:
                try: st.line_chart(df_prog.set_index("Date")["Weight"])
                except: pass
        else: st.info("No progress")

    with tab_c:
        st.subheader("Weekly Check-In")
        with st.form("client_checkin_form"):
            week_start = st.date_input("Week Starting")
            feedback = st.text_area("Your weekly feedback / notes")
            checkin_img = st.file_uploader("Upload Image (optional)", type=["png","jpg","jpeg"])
            if st.form_submit_button("Submit Check-In"):
                ts = datetime.utcnow().isoformat()
                img_url = ""
                if checkin_img:
                    img_bytes = checkin_img.read()
                    img_url = f"client_uploads/{client_user}_{ts}.jpg"
                    os.makedirs("client_uploads", exist_ok=True)
                    with open(img_url,"wb") as f: f.write(img_bytes)
                row = [client_user,str(week_start),feedback,"Submitted",ts,img_url]
                if USE_GOOGLE:
                    append_row("checkins", row)
                else:
                    st.session_state["checkins"].append(dict(
                        ClientUsername=client_user,
                        WeekStartDate=str(week_start),
                        Feedback=feedback,
                        Submitted="Submitted",
                        Timestamp=ts,
                        ImageURL=img_url
                    ))
                st.success("Check-in submitted!")
                st.session_state.rerun_flag=True

# ---------------------------
# Safe rerun
# ---------------------------
if st.session_state.rerun_flag:
    safe_rerun()

