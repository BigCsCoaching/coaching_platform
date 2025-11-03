import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- Page Setup ---
st.set_page_config(page_title="BigC's Coaching", page_icon="💪", layout="wide")

# --- Custom Styling ---
st.markdown("""
    <style>
        /* Main background */
        .stApp {
            background-color: #0e1117;
            color: white;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #111827;
        }

        /* Titles and text */
        h1, h2, h3, h4 {
            color: #2E86C1 !important;
            font-weight: 800;
        }

        p, li, div, label {
            color: #d1d5db !important;
        }

        /* Buttons */
        button[kind="primary"] {
            background-color: #2E86C1 !important;
            color: white !important;
            border-radius: 10px !important;
            font-weight: bold;
        }

        /* Centered main title */
        .main-title {
            text-align: center;
            font-size: 60px;
            color: #2E86C1;
            font-weight: 900;
            margin-bottom: 0;
        }

        .subtitle {
            text-align: center;
            font-size: 20px;
            color: #888;
            margin-top: 5px;
            margin-bottom: 40px;
        }

        .info-box {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar Navigation ---
page = st.sidebar.radio("Navigation", ["🏠 Home", "👥 Clients", "📊 Progress Tracker", "🍎 Nutrition Log"])

# --- HOME PAGE ---
if page == "🏠 Home":
    st.markdown("<h1 class='main-title'>BigC's Coaching</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>@callumjules</p>", unsafe_allow_html=True)

    st.markdown("""
    <div class='info-box'>
    <h3>Welcome!</h3>
    <p>This platform helps you manage your clients, track workouts, monitor nutrition, and visualize progress — all in one place.</p>
    <p>Use the sidebar to access different sections of your coaching dashboard.</p>
    </div>
    """, unsafe_allow_html=True)

# --- CLIENT MANAGEMENT ---
elif page == "👥 Clients":
    st.header("Client Management")
    st.write("Add and manage your coaching clients below:")

    if "clients" not in st.session_state:
        st.session_state.clients = []

    with st.form("add_client_form"):
        name = st.text_input("Client Name")
        goal = st.text_input("Client Goal")
        submitted = st.form_submit_button("Add Client")

        if submitted and name:
            st.session_state.clients.append({"name": name, "goal": goal})
            st.success(f"✅ Added {name} successfully!")

    if st.session_state.clients:
        st.subheader("Your Clients:")
        for i, client in enumerate(st.session_state.clients):
            with st.expander(f"{client['name']} — {client['goal']}"):
                st.write(f"**Goal:** {client['goal']}")
                st.write("💪 Workout Plan:")
                st.text_area(f"Workout notes for {client['name']}", key=f"workout_{i}")
                st.write("🥗 Nutrition Plan:")
                st.text_area(f"Nutrition notes for {client['name']}", key=f"nutrition_{i}")
                st.write("📈 Progress:")
                st.slider(f"Progress (%) for {client['name']}", 0, 100, 50, key=f"progress_{i}")

# --- PROGRESS TRACKER ---
elif page == "📊 Progress Tracker":
    st.header("Client Progress Tracker")

    st.write("Use this section to visualize progress across clients.")
    if "clients" in st.session_state and st.session_state.clients:
        data = {
            client["name"]: st.session_state.get(f"progress_{i}", 0)
            for i, client in enumerate(st.session_state.clients)
        }
        df = pd.DataFrame(list(data.items()), columns=["Client", "Progress"])

        fig, ax = plt.subplots()
        ax.bar(df["Client"], df["Progress"])
        ax.set_xlabel("Clients")
        ax.set_ylabel("Progress (%)")
        ax.set_title("Client Progress Overview")
        st.pyplot(fig)
    else:
        st.info("Add clients in the 'Clients' tab first.")

# --- NUTRITION LOG ---
elif page == "🍎 Nutrition Log":
    st.header("Nutrition Log")
    st.write("Track your clients' nutrition plans here.")

    if "nutrition_log" not in st.session_state:
        st.session_state.nutrition_log = []

    with st.form("nutrition_form"):
        client_name = st.text_input("Client Name")
        calories = st.number_input("Calories", 0)
        protein = st.number_input("Protein (g)", 0)
        carbs = st.number_input("Carbs (g)", 0)
        fats = st.number_input("Fats (g)", 0)
        submitted = st.form_submit_button("Save Entry")

        if submitted and client_name:
            st.session_state.nutrition_log.append({
                "Client": client_name,
                "Calories": calories,
                "Protein": protein,
                "Carbs": carbs,
                "Fats": fats
            })
            st.success(f"Nutrition entry saved for {client_name}!")

    if st.session_state.nutrition_log:
        st.subheader("Saved Nutrition Entries")
        df = pd.DataFrame(st.session_state.nutrition_log)
        st.dataframe(df)
