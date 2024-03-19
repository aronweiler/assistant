from typing import List
import pandas as pd
import streamlit as st

from navigation import make_sidebar
from src.shared.database.models.task_operations import TaskOperations
from src.shared.database.models.domain.task_model import TaskModel
from src.ui.app.utilities import set_page_config


set_page_config(page_name="Tasks")
make_sidebar()


def highlight_row(s):
    if s["Current State"] == "SUCCESS":
        return ["background-color: #006600"] * len(s)
    elif s["Current State"] == "FAILURE":
        return ["background-color: #990000"] * len(s)
    else:
        return ["background-color: #ffebcc"] * len(s)


def load_tasks(user_id, current_state=None) -> List[TaskModel]:
    task_ops = TaskOperations()
    if current_state and current_state != "---":
        tasks = task_ops.get_tasks_by_user_id_and_state(user_id, current_state)
    else:
        tasks = task_ops.get_tasks_by_user_id(user_id)
    return tasks


def load_task_history(task_id):
    task_ops = TaskOperations()
    return task_ops.get_task_history_by_task_id(task_id)


st.title("User Tasks")

col1, col2 = st.columns([0.25, 0.75])
col1a, col1b, crap = st.columns([0.1, 0.2, 0.7])

user_id = st.session_state.user_id
state_filter = col1.selectbox("Filter By", ["---", "PROGRESS", "SUCCESS", "FAILURE"])
tasks = load_tasks(user_id, state_filter)

if col1a.button("Refresh"):
    tasks = load_tasks(user_id, state_filter)

if col1b.button("Clear Task History"):
    task_ops = TaskOperations()
    task_ops.delete_tasks_by_user_id(user_id)
    tasks = load_tasks(user_id, state_filter)

task_table = [
    [task.name, task.current_state, task.description, task.record_updated]
    for task in tasks
]

df = pd.DataFrame(
    task_table, columns=["Name", "Current State", "Description", "Last Modified"]
)

df = df.sort_values(by="Last Modified", ascending=False)

# Apply the styling function to the DataFrame
df_styled = df.style.apply(highlight_row, axis=1)

st.dataframe(df_styled, hide_index=True, use_container_width=True)

# Look at this when I want to start displaying the task history
# for task in tasks:
#     col1, col2 = st.columns([3, 1])
#     with col1:
#         st.text(f"Name: {task.name}")
#         st.text(f"State: {task.current_state}")
#         st.text(f"Description: {task.description}")
#     with col2:
#         if st.button("Show History", key=task.id):
#             if f"history_{task.id}" not in st.session_state:
#                 st.session_state[f"history_{task.id}"] = True
#             else:
#                 del st.session_state[f"history_{task.id}"]

#     if f'history_{task.id}' in st.session_state:
#         history = load_task_history(task.id)
