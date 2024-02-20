import io
from io import IOBase
import os
import logging
import json
import sys
from typing import Any, List, Optional, Union

import pandas as pd

from langchain.agents import AgentType

from langchain.agents.agent import AgentExecutor
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.schema.language_model import BaseLanguageModel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.tools.tool_registry import register_tool, tool_class
from src.ai.utilities.llm_helper import get_llm
from src.configuration.model_configuration import ModelConfiguration

from src.db.models.domain.file_model import FileModel
from src.db.models.documents import Documents
from src.db.models.user_settings import UserSettings


@tool_class
class SpreadsheetsTool:
    excel_types = [".xls", ".xlsx", ".ods"]
    cached_pandas_dataframes = {}

    def __init__(
        self,
        configuration,
        conversation_manager: ConversationManager,
    ):
        self.conversation_manager = conversation_manager
        self.configuration = configuration
        self.callbacks = []

        self.document_helper = Documents()

    @register_tool(
        display_name="Query Spreadsheet",
        description="Query a spreadsheet using natural language.",
        additional_instructions="This tool transforms your natural language query into Python code to query a spreadsheet using the pandas library.",
        requires_documents=True,
        document_classes=["Spreadsheet"],
        enabled_by_default=False,
        include_in_conversation=False,
        requires_llm=True,
        category="Documents",
    )
    def query_spreadsheet_with_pandas(self, query: str, target_file_id: int):
        """Useful for querying a specific spreadsheet.  If the target document is a 'Spreadsheet', always use this tool.

        Args:
            query (str): The query to use.
            target_file_id (int): The file ID to query."""

        override_file = None
        if self.conversation_manager:
            override_file = self.conversation_manager.tool_kwargs.get(
                "override_file", None
            )

        if override_file is not None:
            target_file_id = int(override_file)

        file = self.document_helper.get_file(target_file_id)

        # Get the setting for the tool model
        tool_model_configuration = ModelConfiguration(
            **json.loads(
                UserSettings()
                .get_user_setting(
                    user_id=self.conversation_manager.user_id,
                    setting_name=f"{self.query_spreadsheet_with_pandas.__name__}_model_configuration",
                    default_value=ModelConfiguration.default().model_dump_json(),
                )
                .setting_value
            )
        )

        llm = get_llm(
            model_configuration=tool_model_configuration,
            streaming=True,
            callbacks=self.conversation_manager.agent_callbacks,
        )

        agent_executor = self.create_pandas_agent(llm=llm, files=[file])

        # self.callbacks is set outside of this class
        results = agent_executor.run(
            input=query,
            handle_parsing_errors=True,
            callbacks=self.conversation_manager.agent_callbacks
        )

        return results

    def create_pandas_agent(
        self,
        llm: BaseLanguageModel,
        files: List[FileModel],
    ) -> AgentExecutor:
        """Create csv agent by loading to a dataframe and using pandas agent."""

        pandas_dataframes = self.get_dataframes(files=files)

        # Get a list of the dataframes in the pandas_dataframes dictionary
        dfs = []
        for key in pandas_dataframes:
            for df in pandas_dataframes[key]:
                dfs.append(df)

        pandas_agent = create_pandas_dataframe_agent(
            llm=llm,
            df=dfs,
            include_df_in_prompt=True,
            number_of_head_rows=5,
            verbose=True,
            # callbacks=self.callbacks,
        )

        return pandas_agent

    def get_dataframes(self, files: List[FileModel], **kwargs: Any) -> dict:
        for file in files:
            if not file.id in self.cached_pandas_dataframes:
                self.cached_pandas_dataframes[file.id] = []

                # Read in the file from the database
                reader = io.BytesIO(self.document_helper.get_file_data(file.id))
                # Check to see if the file extension is in the excel types
                file_extension = os.path.splitext(file.file_name)[1]

                if file_extension in self.excel_types:
                    # If it is an excel type, read it in as an excel file
                    for sheet in pd.ExcelFile(reader, **kwargs).sheet_names:
                        df = pd.read_excel(reader, sheet_name=sheet, **kwargs)
                        self.cached_pandas_dataframes[file.id].append(df)
                else:
                    # Otherwise, read it in as a csv
                    self.cached_pandas_dataframes[file.id].append(
                        pd.read_csv(
                            filepath_or_buffer=reader,
                            on_bad_lines="skip",
                            encoding="ISO-8859-1",
                            **kwargs,
                        )
                    )
            else:
                logging.info(
                    f"File {file.file_name} already in pandas cache, skipping."
                )

        return self.cached_pandas_dataframes


if __name__ == "__main__":
    conversation_manager = ConversationManager(
        conversation_id=None, user_email="aronweiler@gmail.com", prompt_manager=None
    )

    spreadsheets_tool = SpreadsheetsTool(
        configuration=None, conversation_manager=conversation_manager
    )
    result = spreadsheets_tool.query_spreadsheet_with_pandas(
        "What headers are in this file?", 6
    )

    print(result)
