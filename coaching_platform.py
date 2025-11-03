import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Coaching Dashboard", layout="wide")

# --- Sidebar Navigation ---
page = st.sidebar.radio("Navigate", ["🏠 Home", "🧑‍💼 Clients", "🏋️ Workouts", "🍎 Nutrition", "📊 Progress"])

# --- Home Page ---
if page == "🏠 Home":
    st.title("🏋️ Coaching Platform")
    st.write("Welcome to your all-in-one coaching dashboard!")
    st.info("Use the sidebar to manage clients, create workout and nutrition plans, and track progress.")

# --- Clients Page ---
elif page == "🧑‍💼 Clients":
    st.title("Client Management")

    if "clients" not in st.session_state:
        st.session_state.clients = []

    with st.form("add_client"):
        name = st.text_input("Client Name")
        goal = st.text_input("Client Goal")
        submitted = st.form_submit_button("Add Client")
        if submitted and name:
            st.session_state.clients.append({"name": name, "goal": goal})
            st.success(f"Added {name}")

    if st.session_state.clients:
        st.subheader("Your Clients")
        st.table(pd.DataFrame(st.session_state.clients))

# --- Workouts Page ---
elif page == "🏋️ Workouts":
    st.title("Workout Planner")

    if "workouts" not in st.session_state:
        st.session_state.workouts = []

    with st.form("add_workout"):
        exercise = st.text_input("Exercise")
        sets = st.number_input("Sets", 1, 10, 3)
        reps = st.number_input("Reps", 1, 20, 10)
        weight = st.number_input("Weight (kg)", 0, 500, 60)
        add_workout = st.form_submit_button("Add Exercise")

        if add_workout and exercise:
            st.session_state.workouts.append({
                "exercise": exercise,
                "sets": sets,
                "reps": reps,
                "weight": weight
            })
            st.success(f"Added {exercise}")

    if st.session_state.workouts:
        df = pd.DataFrame(st.session_state.workouts)
        st.subheader("Workout Plan")
        st.table(df)

# --- Nutrition Page ---
elif page == "🍎 Nutrition":
    st.title("Nutrition Planner")

    if "nutrition" not in st.session_state:
        st.session_state.nutrition = []

    with st.form("add_meal"):
        meal = st.text_input("Meal / Food Item")
        calories = st.number_input("Calories", 0, 2000, 400)
        protein = st.number_input("Protein (g)", 0, 200, 20)
        carbs = st.number_input("Carbs (g)", 0, 200, 40)
        fats = st.number_input("Fats (g)", 0, 100, 10)
        add_meal = st.form_submit_button("Add Meal")

        if add_meal and meal:
            st.session_state.nutrition.append({
                "meal": meal,
                "calories": calories,
                "protein": protein,
                "carbs": carbs,
                "fats": fats
            })
            st.success(f"Added {meal}")

    if st.session_state.nutrition:
        df = pd.DataFrame(st.session_state.nutrition)
        st.subheader("Daily Nutrition")
        st.table(df)
        total_calories = df["calories"].sum()
        st.metric("Total Daily Calories", f"{total_calories} kcal")

# --- Progress Page ---
elif page == "📊 Progress":
    st.title("Progress Tracker")

    if "progress" not in st.session_state:
        st.session_state.progress = []

    with st.form("add_progress"):
        date = st.date_input("Date")
        weight = st.number_input("Weight (kg)", 0, 300, 70)
        add_progress = st.form_submit_button("Add Entry")

        if add_progress:
            st.session_state.progress.append({"date": date, "weight": weight})
            st.success("Progress added!")

    if st.session_state.progress:
        df = pd.DataFrame(st.session_state.progress)
        st.line_chart(df.set_index("date")["weight"])
        st.table(df)
