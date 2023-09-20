from typing import List

import os
import logging
import pandas as pd
import streamlit as st
from streamlit_extras.no_default_selectbox import selectbox
from streamlit_tree_select import tree_select

from src.ai.single_shot_design_decision_generator import SingleShotDesignDecisionGenerator
from src.ai.system_architecture_generator import SystemArchitectureGenerator

from src.configuration.assistant_configuration import SoftwareDevelopmentConfigurationLoader
from src.db.database.creation_utilities import CreationUtilities
from src.db.models.vector_database import VectorDatabase

from src.db.models.documents import Documents

from src.db.models.software_development.projects import Projects
from src.db.models.software_development.domain.project_model import ProjectModel

from src.db.models.software_development.design_decisions import DesignDecisions
from src.db.models.software_development.domain.design_decisions_model import DesignDecisionsModel

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
            "configurations/software_development/openai_config.json",
        )

    def load_configuration(self):
        software_development_configuration_path = self.get_configuration_path()
        if "config" not in st.session_state:
            st.session_state.config = SoftwareDevelopmentConfigurationLoader.from_file(
                software_development_configuration_path
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

    def load_project_design_decisions(self):        
        if st.session_state.project_selectbox != "---":
            project_id = st.session_state.project_selectbox.split(":")[1]

            design_decisions_helper = DesignDecisions()
            design_decisions = design_decisions_helper.get_design_decisions_in_project(project_id)

            with st.expander(f"Design Decisions ({len(design_decisions)})"):
                st.session_state.design_decisions_df = pd.DataFrame(
                    [vars(u) for u in design_decisions], columns=["id", "component", "decision", "details"]
                )
                st.data_editor(
                    st.session_state.design_decisions_df,
                    key="design_decisions_table",
                    num_rows="dynamic",
                    column_config={
                        "id": "Design Decision ID",
                        "component": "Component",
                        "decision": "Decision",
                        "details": "Details",
                    },
                    disabled=["id"],
                )

                if st.button("Save design decisions"):
                    if st.session_state.design_decisions_table:
                        # Handle deleted rows first, because they are done by index
                        for row in st.session_state.design_decisions_table["deleted_rows"]:
                            # Get the id from the deleted row
                            id = st.session_state.design_decisions_df.iloc[row]["id"]
                            design_decisions_helper.delete_design_decision(int(id))
                            st.session_state.design_decisions_df.drop(index=row, inplace=True)

                            st.write(f"Deleted record with id {id}")

                        for row in st.session_state.design_decisions_table["added_rows"]:
                            # Ignore empty rows
                            if len(row) > 0:
                                # Add it to the database
                                design_decisions_helper.create_design_decision(
                                    project_id, row["component"], row["decision"], row["details"]
                                )

                        for row in st.session_state.design_decisions_table["edited_rows"]:
                            # First get the ID of the row
                            id = st.session_state.design_decisions_df.iloc[row]["id"]

                            # Then get the value from the db
                            design_decision = design_decisions_helper.get_design_decision(int(id))

                            # Then update the values
                            design_decision.component = st.session_state.design_decisions_table[
                                "edited_rows"
                            ][row].get("component", design_decision.component)
                            design_decision.decision = st.session_state.design_decisions_table[
                                "edited_rows"
                            ][row].get("decision", design_decision.decision)
                            design_decision.details = st.session_state.design_decisions_table[
                                "edited_rows"
                            ][row].get("details", design_decision.details)

                            design_decisions_helper.update_design_decision(
                                int(id), design_decision.component, design_decision.decision, design_decision.details
                            )

    def load_user_needs(self):
        
        if st.session_state.project_selectbox != "---":
            project_id = st.session_state.project_selectbox.split(":")[1]

            user_needs_helper = UserNeeds()
            user_needs = user_needs_helper.get_user_needs_in_project(project_id)

            with st.expander(f"User Needs ({len(user_needs)})"):
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
            
            with st.expander(f"Requirements ({len(requirements)})"):
                st.session_state.requirements_df = pd.DataFrame(
                    [vars(u) for u in requirements],
                    columns=["id", "user_need_id", "category", "text"],
                )
                st.data_editor(
                    st.session_state.requirements_df,
                    key="requirements_table",
                    num_rows="dynamic",
                    column_config={
                        "id": st.column_config.NumberColumn(
                            "ID",
                            width=None,
                            disabled=True,

                        ),
                        "user_need_id": "User need ID",
                        "category": "Category",
                        "text": st.column_config.TextColumn(
                            "Requirement Text",
                            help="Requirement text goes here",
                            width="large",
                        )                      
                    },
                    disabled=["id"],
                    width=2000
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

                if st.button("Generate design decisions"):
                    self.generate_design_decisions()

                if st.button("Generate system architecture"):
                    self.generate_system_architecture()

    def load_additional_inputs(self):
    
        if st.session_state.project_selectbox != "---":
            project_id = st.session_state.project_selectbox.split(":")[1]

            documents_helper = Documents()
            additional_inputs_helper = AdditionalDesignInputs()
            additional_inputs = additional_inputs_helper.get_design_inputs_for_project(
                    project_id
                )
            
            with st.expander(f"Additional Inputs ({len(additional_inputs)})"):
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

    def generate_specifications(self, requirement_id):
        requirements_helper = Requirements()
        requirement = requirements_helper.get_requirement(requirement_id)

        st.write("Generating for: " + requirement.text)

    def generate_design_decisions(self):
        design_generator = SingleShotDesignDecisionGenerator(st.session_state.config.design_decision_generator)
        design_generator.generate(
            st.session_state.project_selectbox.split(":")[1]
        )

    def generate_system_architecture(self):
        system_architecture_generator = SystemArchitectureGenerator(st.session_state.config.design_decision_generator)
        result = system_architecture_generator.generate(
            st.session_state.project_selectbox.split(":")[1]
        )

        st.container().write(result)
        

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

    general_ui.load_project_design_decisions()

    general_ui.load_user_needs()

    general_ui.load_requirements()

    general_ui.load_additional_inputs()
