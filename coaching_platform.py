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
    st.write("Use this app to manage your clients, track workouts, nutrition, and progress — all in one place.")
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
                st.warning("Client already exists!")

    # --- Select Client ---
    if st.session_state.clients:
        st.subheader("Select a Client")
        selected_client = st.selectbox(
            "Choose a client to view dashboard",
            list(st.session_state.clients.keys())
        )

        client_data = st.session_state.clients[selected_client]
        st.markdown(f"### 🧑 {selected_client}")
        st.caption(f"Goal: {client_data['goal']}")

        # Tabs inside the client's page
        tab1, tab2, tab3 = st.tabs(["🏋️ Workouts", "🍎 Nutrition", "📊 Progress"])

        # ---------- WORKOUTS ----------
        with tab1:
            st.subheader("Workout Plan")

            with st.form(f"workout_form_{selected_client}"):
                exercise = st.text_input("Exercise")
                sets = st.number_input("Sets", 1, 10, 3)
                reps = st.number_input("Reps", 1, 20, 10)
                weight = st.number_input("Weight (kg)", 0, 500, 60)
                add_workout = st.form_submit_button("Add Exercise")

                if add_workout and exercise:
                    client_data["workouts"].append({
                        "exercise": exercise,
                        "sets": sets,
                        "reps": reps,
                        "weight": weight
                    })
                    st.success(f"Added {exercise}")

            if client_data["workouts"]:
                df = pd.DataFrame(client_data["workouts"])
                st.table(df)

        # ---------- NUTRITION ----------
        with tab2:
            st.subheader("Nutrition Plan")

            with st.form(f"nutrition_form_{selected_client}"):
                meal = st.text_input("Meal / Food")
                calories = st.number_input("Calories", 0, 2000, 400)
                protein = st.number_input("Protein (g)", 0, 200, 20)
                carbs = st.number_input("Carbs (g)", 0, 200, 40)
                fats = st.number_input("Fats (g)", 0, 100, 10)
                add_meal = st.form_submit_button("Add Meal")

                if add_meal and meal:
                    client_data["nutrition"].append({
                        "meal": meal,
                        "calories": calories,
                        "protein": protein,
                        "carbs": carbs,
                        "fats": fats
                    })
                    st.success(f"Added {meal}")

            if client_data["nutrition"]:
                df = pd.DataFrame(client_data["nutrition"])
                st.table(df)
                st.metric("Total Calories", f"{df['calories'].sum()} kcal")

        # ---------- PROGRESS ----------
        with tab3:
            st.subheader("Progress Tracking")

            with st.form(f"progress_form_{selected_client}"):
                date = st.date_input("Date")
                weight = st.number_input("Weight (kg)", 0, 300, 70)
                add_progress = st.form_submit_button("Add Progress")

                if add_progress:
                    client_data["progress"].append({"date": date, "weight": weight})
                    st.success("Progress added!")

            if client_data["progress"]:
                df = pd.DataFrame(client_data["progress"])
                if not df.empty:
                    st.line_chart(df.set_index("date")["weight"])
                    st.table(df)

    else:
        st.info("No clients yet — add one using the form above.")
