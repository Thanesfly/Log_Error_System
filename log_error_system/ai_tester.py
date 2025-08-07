# ai_tester.py
import streamlit as st
import json
import os
from ai_model.model import predict_solution
from ai_model.train_model import train_and_save_model

DB_PATH = "solutions_dynamic.json"

st.title("🧠 AI Log Message Solution Tester")

# --- Test AI Prediction ---
user_input = st.text_area("Enter a log error message to test AI prediction:")

if st.button("Predict Solution"):
    if user_input.strip():
        try:
            predicted = predict_solution(user_input)
            st.success(f"🤖 Predicted Solution:\n\n{predicted}")
        except Exception as e:
            st.error(f"AI Prediction Failed: {e}")
    else:
        st.warning("Please enter a log message.")

# --- Add to Training Data ---
st.markdown("---")
st.markdown("### 📚 Add New Training Example")

new_msg = st.text_input("New log message")
new_sol = st.text_input("Expected solution")

if st.button("Add and Retrain Model"):
    if new_msg.strip() and new_sol.strip():
        # Load existing database
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        data[new_msg.strip()] = new_sol.strip()

        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Retrain model
        try:
            train_and_save_model()
            st.success("✅ Added and retrained model successfully!")
        except Exception as e:
            st.error(f"Retraining failed: {e}")
    else:
        st.warning("Both message and solution are required.")
