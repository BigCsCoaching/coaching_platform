# coaching_platform.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import json
from datetime import datetime

# ------------------------------
# File paths for storing data
# ------------------------------
USERS_FILE = "users.json"
PLANS_FILE = "plans.json"
PROGRESS_FILE = "progress.json"

# ------------------------------
# Helper functions
# ------------------------------
def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return {}

def save_data(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

# ------------------------------
# User Authentication
# ------------------------------
def register_user(username, password, role):
    users = load_data(USERS_FILE)
    if username in users:
        st.error("Username already exists.")
    else:
        users[username] = {"password": password, "role": role}
        save_data(USERS_FILE, users)
        st.success(f"{role.capitalize()} registered successfully!")

def login_user(username, password):
    users = load_data(USERS_FILE)
    if username in users and users[username]["password"] == password:
        return users[username]["role"]
    else:
        st.error("Invalid username or password.")
        return None

# ------------------------------
# Plan Management
# ------------------------------
def create_plan(client, plan_name, exercises):
    plans = load_data(PLANS_FILE)
    if client not in plans:
        plans[client] = []
    plans[client].append({"plan_name": plan_name, "exercises": exercises})
    save_data(PLANS_FILE, plans)
    st.success(f"Plan '{plan_name}' added for {client}.")

def view_plans(client):
    plans = load_data(PLANS_FILE)
    if client in plans and plans[client]:
        for idx, plan in enumerate(plans[client], start=1):
            with st.expander(f"Plan {idx}: {plan['plan_name']}"):
                for ex in plan["exercises"]:
                    st.write(f"- {ex}")
    else:
        st.info("No plans found.")

# ------------------------------
# Progress Tracking
# ------------------------------
def log_progress(client, metric, value):
    progress = load_data(PROGRESS_FILE)
    if client not in progress:
        progress[client] = []
    progress[client].append({"metric": metric, "value": value, "date": str(datetime.now().date())})
    save_data(PROGRESS_FILE, progress)
    st.success(f"Logged {metric} = {value} for {client}.")

def show_progress(client):
    progress = load_data(PROGRESS_FILE)
    if client not in progress or not progress[client]:
        st.info("No progress data yet.")
        return

    df = pd.DataFrame(progress[client])
    df['date'] = pd.to_datetime(df['date'])
    st.dataframe(df)

    # Plot all metrics in one chart
    plt.figure(figsize=(8, 4))
    metrics = df['metric'].unique()
    for m in metrics:
        metric_df = df[df['metric'] == m]
        plt.plot(metric_df['date'], metric_df['value'], marker='o', label=m)
    plt.xlabel("Date")
    plt.ylabel("Value")
    plt.title(f"Progress for {client}")
    plt.legend()
    st.pyplot(plt)
    plt.clf()

# ------------------------------
# Streamlit App
# ------------------------------
st.set_page_config(page_title="Coaching Platform", layout="wide")
st.title("💪 Coaching Platform")

menu = ["Home", "Register", "Login"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Home":
    st.subheader("Welcome to the Coaching Platform")
    st.write("Use the sidebar to Register or Login.")

elif choice == "Register":
    st.subheader("Register New User")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["coach", "client"])
    if st.button("Register"):
        register_user(username, password, role)

elif choice == "Login":
    st.subheader("Login")
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        role = login_user(username, password)
        if role:
            st.success(f"Logged in as {role}")

            if role == "coach":
                st.subheader("Coach Dashboard")
                coach_menu = ["Create Plan", "View Client Plans", "View All Clients Progress"]
                coach_choice = st.selectbox("Coach Menu", coach_menu)

                if coach_choice == "Create Plan":
                    client_name = st.text_input("Client Username")
                    plan_name = st.text_input("Plan Name")
                    exercises = st.text_area("Exercises (comma-separated)").split(",")
                    if st.button("Add Plan"):
                        exercises = [ex.strip() for ex in exercises if ex.strip()]
                        create_plan(client_name, plan_name, exercises)

                elif coach_choice == "View Client Plans":
                    client_name = st.text_input("Client Username to View")
                    if st.button("Show Plans"):
                        view_plans(client_name)

                elif coach_choice == "View All Clients Progress":
                    progress_data = load_data(PROGRESS_FILE)
                    if progress_data:
                        client_list = list(progress_data.keys())
                        selected_client = st.selectbox("Select Client", client_list)
                        if st.button("Show Progress"):
                            show_progress(selected_client)
                    else:
                        st.info("No progress data yet.")

            elif role == "client":
                st.subheader("Client Dashboard")
                client_menu = ["View Plans", "Log Progress", "View Progress"]
                client_choice = st.selectbox("Client Menu", client_menu)

                if client_choice == "View Plans":
                    view_plans(username)

                elif client_choice == "Log Progress":
                    metric = st.text_input("Metric (e.g., weight, bench press)")
                    value = st.number_input("Value", min_value=0.0)
                    if st.button("Log Progress"):
                        log_progress(username, metric, value)

                elif client_choice == "View Progress":
                    show_progress(username)
