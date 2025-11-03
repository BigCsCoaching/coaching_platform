import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Coaching Platform", layout="wide")

# ---------- INITIALISE STATE ----------
if "clients" not in st.session_state:
    st.session_state.clients = {}

# ---------- SIDEBAR ----------
st.sidebar.title("🏋️ Coaching Platform")
page = st.sidebar.radio("Navigation", ["🏠 Home", "🧑‍💼 Clients"])

# ---------- HOME ----------
if page == "🏠 Home":
    st.title("Welcome to your Coaching Dashboard")
    st.write("Use this app to manage your clients, track workouts, nutrition and progress — all in one place.")
    st.info("Go to the 'Clients' page in the sidebar to get started.")

# ---------- CLIENT MANAGEMENT ----------
elif page == "🧑‍💼 Clients":
    st.title("Client Management")

    # --- Add New Client ---
    with st.form("add_client"):
        name = st.text_input("Client Name")
        goal = st.text_input("Primary Goal")
        submitted = st.form_submit_button("Add Client")
        if submitted and name:
            if name not in st.session_state.clients:
                st.session_state.clients[name] = {
                    "goal": goal,
                    "workouts": [],
                    "nutrition": [],
                    "progress": []
                }
                st.success(f"Added client {name}")
            else:
