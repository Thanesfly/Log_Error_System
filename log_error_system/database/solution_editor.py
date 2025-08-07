import streamlit as st
import os
import json
import sys
from database.solutions_db import load_solutions, save_solutions
from database.solutions_writer import write_solution, delete_solution

def rerun():
    raise st.script_run_ctx.RerunException(st.script_request_queue.RerunData())

def write_solution(message, solution, path="database/solutions_dynamic.json"):
    ...


from database.solutions_db import load_solutions, save_solutions
from database.solutions_writer import write_solution, delete_solution
def render_solution_editor():
    st.set_page_config(page_title="📚 Solution Database Manager")

    st.title("📚 Solution Database Manager")
    st.markdown("Manage saved solutions: search, edit, add, or delete log fixes.")

    # Load DB
    db_file = "database/solutions_dynamic.json"
    if not os.path.exists(db_file):
        st.error("❌ Database file not found.")
        st.stop()

    solutions = load_solutions()
    if not solutions:
        st.info("ℹ️ No solutions available yet.")

    # 🔍 Search Bar
    st.subheader("🔎 Search Existing Solutions")
    search_query = st.text_input("Search by log message or solution:")

    filtered = {
        msg: sol for msg, sol in solutions.items()
        if search_query.lower() in msg.lower() or search_query.lower() in sol.lower()
    } if search_query else dict(sorted(solutions.items()))

    # ✏️ Display All or Filtered Entries
    st.subheader("📖 Existing Entries")
    if filtered:
        for message, solution in filtered.items():
            with st.expander(message, expanded=False):
                edited_solution = st.text_area("Edit Solution", value=solution, key=f"text_{message}")
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("💾 Save", key=f"save_{message}"):
                        write_solution(message, edited_solution.strip())
                        st.success("✅ Saved")
                with col2:
                    if st.button("🗑️ Delete", key=f"delete_{message}"):
                        if delete_solution(message):
                            st.success("🗑️ Deleted")
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete.")
    else:
        st.info("🔍 No matching entries found.")

    # ➕ Add New Entry
    st.markdown("---")
    st.subheader("➕ Add New Solution")

    new_msg = st.text_input("📝 New Log Message")
    new_fix = st.text_area("💡 Suggested Solution")

    if st.button("➕ Add Entry"):
        if new_msg.strip() == "" or new_fix.strip() == "":
            st.warning("⚠️ Please fill in both fields.")
        elif new_msg.strip() in solutions:
            st.warning("⚠️ This message already exists in the database.")
        else:
            write_solution(new_msg.strip(), new_fix.strip())
            st.success("✅ New entry added.")
            st.rerun()

