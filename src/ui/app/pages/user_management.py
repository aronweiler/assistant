import streamlit as st
from passlib.hash import pbkdf2_sha256 as hasher

from src.shared.database.models.domain.user_model import UserModel
from src.shared.database.models.users import Users
from navigation import make_sidebar
from src.ui.app.utilities import set_page_config

set_page_config(page_name="Chat")

make_sidebar()

users_db = Users()

# Default to not editing
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

if "create_user_mode" not in st.session_state:
    st.session_state.create_user_mode = False

if st.button("Create User", key="create_user"):
    st.session_state.create_user_mode = True

if st.session_state.create_user_mode:
    with st.form("Create User Form"):
        new_name = st.text_input("Name", value="")
        new_age = st.number_input("Age", value=0)
        new_location = st.text_input("Location", value="")
        new_email = st.text_input("Email", value="")
        new_password = st.text_input("Password", value="", type="password")
        new_is_admin = st.checkbox("Admin User", value=False)
        new_enabled = st.checkbox("Enabled", value=True)
        submitted = st.form_submit_button("Save New User")
        if submitted:
            users_db.create_user(
                email=new_email,
                password_hash=hasher.hash(new_password),
                name=new_name,
                age=new_age,
                location=new_location,
                is_admin=new_is_admin,
                enabled=new_enabled,
            )
            st.success("New user created successfully!")
            st.session_state.create_user_mode = False
            st.session_state.edit_mode = False
            st.rerun()

else:

    # Fetch all users
    all_users = users_db.get_all_users()
    user_options = [(user.name, user.id) for user in all_users]

    # Dropdown to select a user
    selected_user_id = st.selectbox(
        "Select a User", options=user_options, format_func=lambda x: x[0]
    )

    # Display user details
    selected_user = next(
        (user for user in all_users if user.id == selected_user_id[1]), None
    )
    if selected_user:
        if not st.session_state.edit_mode:
            # Display user details
            st.write(f"Name: {selected_user.name}")
            st.write(f"Age: {selected_user.age}")
            st.write(f"Location: {selected_user.location}")
            st.write(f"Email: {selected_user.email}")
            st.write(f"Is Admin: {selected_user.is_admin}")
            st.write(f"Enabled: {selected_user.enabled}")

            if st.button("Edit User", key="edit_user"):
                st.session_state.edit_mode = True
                st.rerun()

        if st.session_state.edit_mode:
            # Editable fields
            updated_name = st.text_input("Name", value=selected_user.name)
            updated_age = st.number_input("Age", value=selected_user.age)
            updated_location = st.text_input("Location", value=selected_user.location)
            updated_email = st.text_input(
                "Email", value=selected_user.email, disabled=True
            )  # Email should not be editable
            updated_password = st.text_input("New Password", value="", type="password")
            updated_is_admin = st.checkbox("Admin User", value=selected_user.is_admin)
            updated_enabled = st.checkbox("Enabled", value=selected_user.enabled)

            if updated_password and updated_password.strip() != "":
                # If they are resetting the password, hash it
                updated_password_hash = hasher.hash(updated_password)
                # Also invalidate the session
                users_db.clear_user_session(selected_user.id)

            else:
                updated_password_hash = selected_user.password_hash

            if not updated_enabled:
                # If they are disabling the user, invalidate the session
                users_db.clear_user_session(selected_user.id)

            col1, col2 = st.columns(2)

            # Save updated user
            if st.session_state.edit_mode and col1.button("Save User", key="save_user"):
                # Update user information in the database
                updated_user = UserModel(
                    id=selected_user.id,
                    session_created=selected_user.session_created,
                    session_id=selected_user.session_id,
                    # Updated values
                    name=updated_name,
                    age=updated_age,
                    location=updated_location,
                    email=updated_email,
                    password_hash=updated_password_hash,
                    is_admin=updated_is_admin,
                    enabled=updated_enabled,
                )

                users_db.update_user(updated_user)

                # Exit edit mode
                st.session_state.edit_mode = False

                st.success("User updated successfully!")
                st.rerun()

            if col2.button("Cancel", key="cancel_edit"):
                st.session_state.edit_mode = False
                st.rerun()
