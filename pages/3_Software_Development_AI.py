from typing import List

import os
import logging
import pandas as pd
import streamlit as st
from streamlit_extras.no_default_selectbox import selectbox
from streamlit_tree_select import tree_select

from src.configuration.assistant_configuration import ConfigurationLoader
from src.db.database.creation_utilities import CreationUtilities
from src.db.models.vector_database import VectorDatabase

from src.db.models.documents import Documents

from src.db.models.software_development.projects import Projects
from src.db.models.software_development.domain.project_model import ProjectModel

from src.db.models.software_development.user_needs import UserNeeds
from src.db.models.software_development.domain.user_needs_model import UserNeedsModel

from src.db.models.software_development.requirements import Requirements
from src.db.models.software_development.domain.requirements_model import (
    RequirementsModel,
)

from src.db.models.software_development.additional_design_inputs import (
    AdditionalDesignInputs,
)
from src.db.models.software_development.domain.additional_design_inputs_model import (
    AdditionalDesignInputsModel,
)


class SoftwareDevelopmentUI:
    def get_configuration_path(self):
        return os.environ.get(
            "SOFTWARE_DEV_CONFIG_PATH",
            "configurations/console_configs/console_ai.json",
        )

    def load_configuration(self):
        assistant_config_path = self.get_configuration_path()
        if "config" not in st.session_state:
            st.session_state["config"] = ConfigurationLoader.from_file(
                assistant_config_path
            )

    def set_page_config(self):
        st.set_page_config(
            page_title="Jarvis - Software Development",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        st.title(
            st.session_state.get(
                "page_title", "Hey Jarvis 🤖... let's develop software!"
            )
        )

    def show_projects(self):
        with st.sidebar.container():
            st.header("Projects")
            st.write("Here are the projects you are working on:")
            st.write("")

            # Show the projects
            selectbox(
                "Select a project",
                self.get_projects(),
                key="project_selectbox",
                format_func=lambda x: x.split(":")[0],
                on_change=self.load_project,
            )

            st.write("")
            st.write("")

    def handle_create_project(self):
        with st.sidebar.container():
            # Add a new project
            if st.button("Add new project", key="add_new_project"):
                st.text_input("Project name", key="project_name")

            if st.button(
                "Create project",
                disabled=st.session_state.get("project_name", None) == None,
                key="create_project",
                type="primary",
            ):
                self.create_project(st.session_state.project_name)
                st.success(f"Project {st.session_state.project_name} created!")

                st.experimental_rerun()

    def create_project(self, project_name):
        projects_helper = Projects()
        projects_helper.create_project(project_name)

    def get_projects(self) -> List[ProjectModel]:
        projects_helper = Projects()
        return [f"{p.project_name}:{p.id}" for p in projects_helper.get_projects()]
        # return projects_helper.get_projects()

    def delete_project(self, project_id):
        pass

    def load_project(self):
        # Load the whole project from the database
        if st.session_state.project_selectbox:
            st.session_state.page_title = (
                f"Project: {st.session_state.project_selectbox.split(':')[0]}"
            )

    def load_user_needs(self):
        if st.session_state.project_selectbox != "---":
            project_id = st.session_state.project_selectbox.split(":")[1]

            user_needs_helper = UserNeeds()
            user_needs = user_needs_helper.get_user_needs_in_project(project_id)

            st.session_state.user_needs_df = pd.DataFrame(
                [vars(u) for u in user_needs], columns=["id", "category", "text"]
            )
            st.data_editor(
                st.session_state.user_needs_df,
                key="user_needs_table",
                num_rows="dynamic",
                column_config={
                    "id": "User Need ID",
                    "category": "Category",
                    "text": "User Need Text",
                },
                disabled=["id"],
            )

            if st.button("Save user needs"):
                if st.session_state.user_needs_table:
                    # Handle deleted rows first, because they are done by index
                    for row in st.session_state.user_needs_table["deleted_rows"]:
                        # Get the id from the deleted row
                        id = st.session_state.user_needs_df.iloc[row]["id"]
                        user_needs_helper.delete_user_need(int(id))
                        st.session_state.user_needs_df.drop(index=row, inplace=True)

                        st.write(f"Deleted record with id {id}")

                    for row in st.session_state.user_needs_table["added_rows"]:
                        # Ignore empty rows
                        if len(row) > 0:
                            # Add it to the database
                            user_needs_helper.create_user_need(
                                project_id, row["category"], row["text"]
                            )

                    for row in st.session_state.user_needs_table["edited_rows"]:
                        # First get the ID of the row
                        id = st.session_state.user_needs_df.iloc[row]["id"]

                        # Then get the value from the db
                        user_need = user_needs_helper.get_user_need(int(id))

                        # Then update the values
                        user_need.category = st.session_state.user_needs_table[
                            "edited_rows"
                        ][row].get("category", user_need.category)
                        user_need.text = st.session_state.user_needs_table[
                            "edited_rows"
                        ][row].get("text", user_need.text)

                        user_needs_helper.update_user_need(
                            int(id), user_need.category, user_need.text
                        )

    def load_requirements(self):
        if st.session_state.project_selectbox != "---":
            project_id = st.session_state.project_selectbox.split(":")[1]

            requirements_helper = Requirements()
            requirements = requirements_helper.get_requirements_for_project(project_id)

            st.session_state.requirements_df = pd.DataFrame(
                [vars(u) for u in requirements],
                columns=["id", "user_need_id", "category", "text"],
            )
            st.data_editor(
                st.session_state.requirements_df,
                key="requirements_table",
                num_rows="dynamic",
                column_config={
                    "id": "Requirement ID",
                    "user_need_id": "User need ID",
                    "category": "Category",
                    "text": "Requirement Text",
                },
                disabled=["id"],
            )

            if st.button("Save requirements"):
                if st.session_state.requirements_table:
                    # Handle deleted rows first, because they are done by index
                    for row in st.session_state.requirements_table["deleted_rows"]:
                        # Get the id from the deleted row
                        id = st.session_state.requirements_df.iloc[row]["id"]
                        requirements_helper.delete_requirement(int(id))
                        st.session_state.requirements_df.drop(index=row, inplace=True)

                        st.write(f"Deleted record with id {id}")

                    for row in st.session_state.requirements_table["added_rows"]:
                        # Ignore empty rows
                        if len(row) > 0:
                            # Add it to the database
                            requirements_helper.create_requirement(
                                project_id,
                                row["user_need_id"],
                                row["category"],
                                row["text"],
                            )

                    for row in st.session_state.requirements_table["edited_rows"]:
                        # Add it to the database
                        # First get the ID of the row
                        id = st.session_state.requirements_df.iloc[row]["id"]

                        # Then get the value from the db
                        requirement = requirements_helper.get_requirement(int(id))

                        # Then update the values
                        requirement.user_need_id = int(
                            st.session_state.requirements_table["edited_rows"][row].get(
                                "user_need_id", requirement.user_need_id
                            )
                        )
                        requirement.category = st.session_state.requirements_table[
                            "edited_rows"
                        ][row].get("category", requirement.category)
                        requirement.text = st.session_state.requirements_table[
                            "edited_rows"
                        ][row].get("text", requirement.text)

                        requirements_helper.update_requirement(
                            int(id),
                            requirement.user_need_id,
                            requirement.category,
                            requirement.text,
                        )

    def load_additional_inputs(self):
        if st.session_state.project_selectbox != "---":
            project_id = st.session_state.project_selectbox.split(":")[1]

            documents_helper = Documents()
            additional_inputs_helper = AdditionalDesignInputs()
            additional_inputs = additional_inputs_helper.get_design_inputs_for_project(
                project_id
            )

            for additional_input in additional_inputs:
                additional_input.file_id = documents_helper.get_file(
                    additional_input.file_id
                ).file_name

            st.session_state.additional_inputs_df = pd.DataFrame(
                [vars(u) for u in additional_inputs],
                columns=["id", "requirement_id", "file_id", "description"],
            )
            st.data_editor(
                st.session_state.additional_inputs_df,
                key="additional_inputs_table",
                num_rows="dynamic",
                column_config={
                    "id": "Additional Input ID",
                    "requirement_id": "Requirement ID",
                    "file_id": st.column_config.SelectboxColumn(
                        "Associated file",
                        help="The file to use as an additional input",
                        width="large",
                        options=[
                            f"{file.id}:{file.file_name}"
                            for file in documents_helper.get_all_files()
                        ],
                    ),
                    "description": "Description",
                },
                disabled=["id"],
            )

            if st.button("Save additional inputs"):
                if st.session_state.additional_inputs_table:
                    # Handle deleted rows first, because they are done by index
                    for row in st.session_state.additional_inputs_table["deleted_rows"]:
                        # Get the id from the deleted row
                        id = st.session_state.additional_inputs_df.iloc[row]["id"]
                        additional_inputs_helper.delete_design_input(int(id))
                        st.session_state.additional_inputs_df.drop(
                            index=row, inplace=True
                        )

                        st.write(f"Deleted record with id {id}")

                    for row in st.session_state.additional_inputs_table["added_rows"]:
                        # Ignore empty rows
                        if len(row) > 0:
                            # Add it to the database
                            additional_inputs_helper.create_design_input(
                                project_id,
                                row["requirement_id"],
                                row["file_id"].split(":")[0],
                                row["description"],
                            )

                    for row in st.session_state.additional_inputs_table["edited_rows"]:
                        # Add it to the database
                        # First get the ID of the row
                        id = st.session_state.additional_inputs_df.iloc[row]["id"]

                        # Then get the value from the db
                        design_input = additional_inputs_helper.get_design_input(
                            int(id)
                        )

                        # Then update the values
                        design_input.requirement_id = int(
                            st.session_state.additional_inputs_table["edited_rows"][
                                row
                            ].get("requirement_id", design_input.user_need_id)
                        )
                        
                        file_name_and_id = st.session_state.additional_inputs_table[
                            "edited_rows"
                        ][row].get("file_id", design_input.file_id)

                        design_input.file_id = file_name_and_id.split(":")[0]

                        design_input.description = st.session_state.additional_inputs_table[
                            "edited_rows"
                        ][row].get("description", design_input.description)

                        additional_inputs_helper.update_design_input(
                            int(id),
                            design_input.requirement_id,
                            design_input.file_id,
                            design_input.description,
                        )

            # projects_helper = Projects()

            # requirements_helper = Requirements()
            # additional_design_inputs_helper = AdditionalDesignInputs()

            # Load the project
            # project = projects_helper.get_project(project_id)
            # nodes = [{"label": project.project_name, "value": project_id}]

            # Load the user needs associated with the project

            # for user_need in user_needs:
            #     user_need.requirements = [vars(r) for r in requirements_helper.get_requirements_for_user_need(user_need.id)]

            # for user_need in user_needs:
            #     nodes.append({"label": user_need.text, "value": user_need.id})
            #     requirements = requirements_helper.get_requirements_for_user_need(user_need.id)

            #     for requirement in requirements:
            #         additional_design_inputs = additional_design_inputs_helper.get_additional_design_inputs_in_requirement(requirement.id)
            #         requirement.additional_design_inputs = additional_design_inputs

            # {
            #         "label": "Folder B",
            #         "value": "folder_b",
            #         "children": [
            #             {"label": "Sub-folder A", "value": "sub_a"},
            #             {"label": "Sub-folder B", "value": "sub_b"},
            #             {"label": "Sub-folder C", "value": "sub_c"},
            #         ],
            #     },
            #     {
            #         "label": "Folder C",
            #         "value": "folder_c",
            #         "children": [
            #             {"label": "Sub-folder D", "value": "sub_d"},
            #             {
            #                 "label": "Sub-folder E",
            #                 "value": "sub_e",
            #                 "children": [
            #                     {"label": "Sub-sub-folder A", "value": "sub_sub_a"},
            #                     {"label": "Sub-sub-folder B", "value": "sub_sub_b"},
            #                 ],
            #             },
            #             {"label": "Sub-folder F", "value": "sub_f"},
            #         ],
            #     },

            # return_select = tree_select(nodes)
            # st.write(return_select)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    general_ui = SoftwareDevelopmentUI()

    # Always comes first!
    general_ui.load_configuration()

    general_ui.set_page_config()

    general_ui.get_projects()

    general_ui.show_projects()

    general_ui.handle_create_project()

    general_ui.load_project()

    general_ui.load_user_needs()

    st.divider()

    general_ui.load_requirements()

    st.divider()

    general_ui.load_additional_inputs()
