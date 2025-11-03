# coaching_platform.py
# BigC's Coaching - Streamlit app with Google Sheets persistence + no-password coach access + admin area.
# Save this file and deploy. See top comments for requirements & secrets setup.

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import json
from datetime import datetime
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
# Configuration & Utilities
# ---------------------------
APP_TITLE = "BigC's Coaching"
APP_SUBTITLE = "@callumjules"
ADMIN_SECRET_KEY = "ADMIN_PASS"  # Streamlit secret key name for admin pass
DEFAULT_ADMIN_PASS = "bigc_admin_pass"  # change before public use

# Google Sheet name
GSHEET_NAME = "BigC Coaching Data"

st.set_page_config(page_title=APP_TITLE, page_icon="💪", layout="wide")

# --- Styling (keeps the look you liked) ---
st.markdown(
    """
    <style>
        .stApp { background-color: #0e1117; color: white; }
        section[data-testid="stSidebar"] { background-color: #111827; }
        h1, h2, h3, h4 { color: #2E86C1 !important; font-weight: 800; }
        p, li, div, label { color: #d1d5db !important; }
        .main-title { text-align: center; font-size: 48px; color: #2E86C1; font-weight: 900; margin-bottom: 0; }
        .subtitle { text-align: center; font-size: 18px; color: #888; margin-top: 5px; margin-bottom: 30px; }
        .info-box { background: rgba(255,255,255,0.03); border-radius: 12px; padding: 16px; margin-top: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# Google Sheets Helpers
# ---------------------------
def gs_auth():
    """
    Try to authenticate to Google Sheets via:
     1) st.secrets["gcp_service_account"] (Streamlit Cloud)
     2) local file 'service_account.json'
    Returns gspread Client or raises Exception.
    """
    if not USE_GOOGLE:
        raise RuntimeError("gspread or oauth2client not installed.")
    # 1) st.secrets
    if "gcp_service_account" in st.secrets:
        try:
            raw = st.secrets["gcp_service_account"]
            creds_json = json.loads(raw)
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
            client = gspread.authorize(creds)
            return client
        except Exception as e:
            raise RuntimeError(f"Failed to auth from st.secrets: {e}")
    # 2) local service_account.json
    if os.path.exists("service_account.json"):
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
            client = gspread.authorize(creds)
            return client
        except Exception as e:
            raise RuntimeError(f"Failed to auth from service_account.json: {e}")
    raise RuntimeError("No Google credentials found. Put service account JSON in st.secrets['gcp_service_account'] or upload service_account.json")

def ensure_sheets_structure(gc):
    """
    Ensure the spreadsheet exists and has the required worksheets.
    Returns the gspread.Spreadsheet object.
    """
    try:
        try:
            sh = gc.open(GSHEET_NAME)
        except gspread.SpreadsheetNotFound:
            sh = gc.create(GSHEET_NAME)
            # Note: on some accounts you may need to share the sheet to your service account email manually.
        # Ensure each worksheet exists
        expected = {
            "clients": ["Name", "Goal"],
            "workouts": ["Client", "Workout", "Details", "Timestamp"],
            "nutrition": ["Client", "Calories", "Protein", "Carbs", "Fats", "Timestamp"],
            "progress": ["Client", "Date", "Weight", "Notes", "Timestamp"],
            "coaches": ["Username"]  # simple list of allowed coach names (no password)
        }
        for title, headers in expected.items():
            try:
                ws = sh.worksheet(title)
            except gspread.WorksheetNotFound:
                ws = sh.add_worksheet(title=title, rows=1000, cols=max(10, len(headers)))
                ws.append_row(headers)
        return sh
    except Exception as e:
        raise RuntimeError(f"Failed ensuring spreadsheet structure: {e}")

def read_sheet_to_df(sh, worksheet_name):
    ws = sh.worksheet(worksheet_name)
    df = get_as_dataframe(ws, evaluate_formulas=True, header=0, skip_blank_lines=True)
    # Drop entirely empty rows that gspread includes
    df = df.dropna(how="all")
    return df

def append_row(sh, worksheet_name, row_values):
    ws = sh.worksheet(worksheet_name)
    ws.append_row(row_values)

# ---------------------------
# Local fallback helpers (session-state)
# ---------------------------
def init_local_storage():
    if "local_clients" not in st.session_state:
        st.session_state.local_clients = []
    if "local_workouts" not in st.session_state:
        st.session_state.local_workouts = []
    if "local_nutrition" not in st.session_state:
        st.session_state.local_nutrition = []
    if "local_progress" not in st.session_state:
        st.session_state.local_progress = []
    if "coaches" not in st.session_state:
        st.session_state.coaches = []

# ---------------------------
# App state helpers
# ---------------------------
if "role" not in st.session_state:
    st.session_state.role = None
if "user" not in st.session_state:
    st.session_state.user = None
if "admin" not in st.session_state:
    st.session_state.admin = False

# ---------------------------
# Try to connect to Google Sheets
# ---------------------------
gclient = None
gsh = None
gs_ok = False
google_error = None
if USE_GOOGLE:
    try:
        gclient = gs_auth()
        gsh = ensure_sheets_structure(gclient)
        gs_ok = True
    except Exception as e:
        google_error = str(e)
else:
    google_error = "gspread or oauth2client not installed in environment."

# If Google not available, init local storage
if not gs_ok:
    init_local_storage()

# ---------------------------
# Header / Landing
# ---------------------------
st.markdown(f"<h1 class='main-title'>{APP_TITLE}</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='subtitle'>{APP_SUBTITLE}</p>", unsafe_allow_html=True)

if not gs_ok:
    st.warning("Google Sheets not connected — using local (temporary) storage. Reason: " + (google_error or "unknown"))

# ---------------------------
# Simple role selection & login
# ---------------------------
with st.sidebar:
    st.markdown("### Access")
    role_choice = st.radio("Enter as:", ["Coach (no password)", "Admin (password)"], index=0)
    if role_choice == "Coach (no password)":
        name = st.text_input("Your name (Coach)", key="coach_name")
        if name:
            st.session_state.role = "coach"
            st.session_state.user = name
        else:
            if st.session_state.role != "coach":
                st.session_state.role = None
                st.session_state.user = None
    else:
        # Admin path
        admin_input = st.text_input("Admin password", type="password", key="admin_pass")
        admin_pass = st.secrets.get(ADMIN_SECRET_KEY, DEFAULT_ADMIN_PASS) if hasattr(st, "secrets") else DEFAULT_ADMIN_PASS
        if admin_input:
            if admin_input == admin_pass:
                st.session_state.role = "admin"
                st.session_state.user = "admin"
                st.session_state.admin = True
                st.success("Admin access granted")
            else:
                st.session_state.role = None
                st.session_state.user = None
                st.session_state.admin = False
                st.error("Wrong admin password")

# ---------------------------
# Utility: load data either from Google Sheets or session-state
# ---------------------------

def load_clients():
    if gs_ok:
        df = read_sheet_to_df(gsh, "clients")
        if df.empty:
            return []
        records = df.to_dict(orient="records")
        return records
    else:
        return st.session_state.local_clients

def load_workouts(client_name=None):
    if gs_ok:
        df = read_sheet_to_df(gsh, "workouts")
        if df.empty:
            return []
        if client_name:
            return df[df["Client"] == client_name].to_dict(orient="records")
        return df.to_dict(orient="records")
    else:
        if client_name:
            return [r for r in st.session_state.local_workouts if r["Client"] == client_name]
        return st.session_state.local_workouts

def load_nutrition(client_name=None):
    if gs_ok:
        df = read_sheet_to_df(gsh, "nutrition")
        if df.empty:
            return []
        if client_name:
            return df[df["Client"] == client_name].to_dict(orient="records")
        return df.to_dict(orient="records")
    else:
        if client_name:
            return [r for r in st.session_state.local_nutrition if r["Client"] == client_name]
        return st.session_state.local_nutrition

def load_progress(client_name=None):
    if gs_ok:
        df = read_sheet_to_df(gsh, "progress")
        if df.empty:
            return []
        if client_name:
            return df[df["Client"] == client_name].to_dict(orient="records")
        return df.to_dict(orient="records")
    else:
        if client_name:
            return [r for r in st.session_state.local_progress if r["Client"] == client_name]
        return st.session_state.local_progress

# ---------------------------
# Utility: append/save functions
# ---------------------------
def save_client(name, goal):
    timestamp = datetime.utcnow().isoformat()
    if gs_ok:
        append_row(gsh, "clients", [name, goal])
    else:
        st.session_state.local_clients.append({"Name": name, "Goal": goal})

def save_workout(client, workout, details):
    ts = datetime.utcnow().isoformat()
    if gs_ok:
        append_row(gsh, "workouts", [client, workout, details, ts])
    else:
        st.session_state.local_workouts.append({"Client": client, "Workout": workout, "Details": details, "Timestamp": ts})

def save_nutrition(client, calories, protein, carbs, fats):
    ts = datetime.utcnow().isoformat()
    if gs_ok:
        append_row(gsh, "nutrition", [client, calories, protein, carbs, fats, ts])
    else:
        st.session_state.local_nutrition.append({"Client": client, "Calories": calories, "Protein": protein, "Carbs": carbs, "Fats": fats, "Timestamp": ts})

def save_progress(client, date_obj, weight, notes):
    ts = datetime.utcnow().isoformat()
    date_str = date_obj.isoformat() if hasattr(date_obj, "isoformat") else str(date_obj)
    if gs_ok:
        append_row(gsh, "progress", [client, date_str, weight, notes, ts])
    else:
        st.session_state.local_progress.append({"Client": client, "Date": date_str, "Weight": weight, "Notes": notes, "Timestamp": ts})

# ---------------------------
# Main App (after role set)
# ---------------------------
if st.session_state.role is None:
    st.info("Select access on the left (Coach or Admin) to continue.")
    st.stop()

# ---------- Admin View ----------
if st.session_state.admin:
    st.markdown("## Admin Dashboard 🔐")
    st.write("You have full access to all data and can view / export sheets below.")

    if gs_ok:
        # Show each sheet as dataframe and allow CSV download
        for sheetname in ["clients", "workouts", "nutrition", "progress", "coaches"]:
            st.subheader(sheetname.capitalize())
            try:
                df = read_sheet_to_df(gsh, sheetname)
            except Exception as e:
                st.error(f"Failed to read {sheetname}: {e}")
                continue
            if df is None or df.empty:
                st.info("No records.")
                continue
            st.dataframe(df)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(label=f"Download {sheetname} CSV", data=csv, file_name=f"{sheetname}.csv", mime="text/csv")
    else:
        st.warning("Google Sheets not connected — admin can view local session data.")
        st.subheader("Local Clients")
        st.write(st.session_state.local_clients)
        st.subheader("Local Workouts")
        st.write(st.session_state.local_workouts)
        st.subheader("Local Nutrition")
        st.write(st.session_state.local_nutrition)
        st.subheader("Local Progress")
        st.write(st.session_state.local_progress)

    st.markdown("---")
    if st.button("Log out admin"):
        st.session_state.admin = False
        st.session_state.role = None
        st.session_state.user = None
        st.experimental_rerun()

# ---------- Coach View (no password) ----------
else:
    coach_name = st.session_state.user or "Coach"
    st.markdown(f"## Welcome, {coach_name} 👋")
    st.write("Add clients, workouts, and track progress for each client below.")

    # Load clients (from sheet or local)
    clients = load_clients()
    # clients might be a list of dicts; unified format:
    client_names = []
    if gs_ok:
        # Google sheet clients use header 'Name' and 'Goal'
        client_names = [r.get("Name") for r in clients if r.get("Name")]
    else:
        client_names = [r.get("name") for r in clients]

    st.sidebar.markdown("### Quick client actions")
    new_client_name = st.sidebar.text_input("New client name")
    new_client_goal = st.sidebar.text_input("New client goal")
    if st.sidebar.button("Create client"):
        if not new_client_name:
            st.sidebar.error("Name required")
        else:
            # Save
            if gs_ok:
                save_client(new_client_name, new_client_goal)
                st.sidebar.success("Client saved to Google Sheets.")
            else:
                st.session_state.local_clients.append({"name": new_client_name, "goal": new_client_goal})
                st.sidebar.success("Client saved locally.")
            st.experimental_rerun()

    # Refresh clients after possible create
    clients = load_clients()
    if gs_ok:
        client_options = [r.get("Name") for r in clients if r.get("Name")]
    else:
        client_options = [r.get("name") for r in clients]

    if not client_options:
        st.info("No clients yet. Create one from the sidebar.")
        st.stop()

    selected_client = st.selectbox("Select client", client_options)

    if gs_ok:
        client_display_name = selected_client
        client_goal = ""
        for r in clients:
            if r.get("Name") == selected_client:
                client_goal = r.get("Goal", "")
                break
    else:
        client_display_name = selected_client
        client_goal = ""
        for r in clients:
            if r.get("name") == selected_client:
                client_goal = r.get("goal", "")
                break

    st.markdown(f"### {client_display_name}")
    if client_goal:
        st.caption(f"Goal: {client_goal}")

    # Tabs for this client
    tab_w, tab_n, tab_p = st.tabs(["🏋️ Workouts", "🍎 Nutrition / Macros", "📈 Progress"])

    # --- Workouts Tab ---
    with tab_w:
        st.subheader("Workouts")
        with st.form("workout_entry"):
            workout_name = st.text_input("Workout name")
            workout_details = st.text_area("Details (sets, reps, notes)")
            submit = st.form_submit_button("Save Workout")
            if submit:
                save_workout(client_display_name, workout_name, workout_details)
                st.success("Workout saved")
                st.experimental_rerun()

        # show existing
        wdata = load_workouts(client_display_name)
        if wdata:
            if gs_ok:
                wdf = pd.DataFrame(wdata)
            else:
                wdf = pd.DataFrame(wdata)
            st.dataframe(wdf)

    # --- Nutrition Tab ---
    with tab_n:
        st.subheader("Nutrition / Macros")
        with st.form("nutrition_entry"):
            cals = st.number_input("Calories", min_value=0)
            prot = st.number_input("Protein (g)", min_value=0)
            carbs = st.number_input("Carbs (g)", min_value=0)
            fats = st.number_input("Fats (g)", min_value=0)
            submit = st.form_submit_button("Save Macros")
            if submit:
                save_nutrition(client_display_name, cals, prot, carbs, fats)
                st.success("Nutrition saved")
                st.experimental_rerun()

        ndata = load_nutrition(client_display_name)
        if ndata:
            ndf = pd.DataFrame(ndata)
            st.dataframe(ndf)
            st.metric("Total Calories (latest)", f"{ndf.iloc[-1]['Calories']}" if not ndf.empty else "0")

    # --- Progress Tab ---
    with tab_p:
        st.subheader("Progress")
        with st.form("progress_entry"):
            pdate = st.date_input("Date")
            pweight = st.number_input("Weight (kg)", min_value=0.0)
            pnotes = st.text_area("Notes (optional)")
            submit = st.form_submit_button("Save Progress")
            if submit:
                save_progress(client_display_name, pdate, pweight, pnotes)
                st.success("Progress saved")
                st.experimental_rerun()

        pdata = load_progress(client_display_name)
        if pdata:
            # Normalize date column types
            pdf = pd.DataFrame(pdata)
            if "Date" in pdf.columns:
                try:
                    pdf["Date"] = pd.to_datetime(pdf["Date"]).dt.date
                except Exception:
                    pass
            st.dataframe(pdf)
            if "Weight" in pdf.columns:
                try:
                    st.line_chart(pd.DataFrame(pdf).set_index("Date")["Weight"])
                except Exception:
                    pass

    # Logout
    if st.button("Log out"):
        st.session_state.role = None
        st.session_state.user = None
        st.experimental_rerun()
