import io
from io import IOBase
import os
import logging
import json
from typing import Any, List, Optional, Union

import pandas as pd

from langchain.agents import AgentType

from langchain.agents.agent import AgentExecutor
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.schema.language_model import BaseLanguageModel


from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.llm_helper import get_tool_llm

from src.db.models.domain.file_model import FileModel
from src.db.models.documents import Documents


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

    def query_spreadsheet(self, query: str, target_file_id: int):
        """Useful for querying a specific spreadsheet.  If the target document is a 'Spreadsheet', always use this tool.

        Args:
            query (str): The query to use.
            target_file_id (int): The file ID to query."""

        override_file = self.conversation_manager.tool_kwargs.get("override_file", None)
        if override_file is not None:
            target_file_id = int(override_file)

        if self.conversation_manager.tool_kwargs.get("use_pandas", False):
            return self.query_spreadsheet_pandas(query, target_file_id)
        else:
            return self.query_spreadsheet_text(query, target_file_id)

    def query_spreadsheet_pandas(self, query: str, target_file_id: int):
        file = self.document_helper.get_file(target_file_id)

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.query_spreadsheet_pandas.__name__,
            streaming=True,
            callbacks=self.conversation_manager.agent_callbacks,
        )

        agent = self.create_pandas_agent(llm=llm, files=[file])

        # self.callbacks is set outside of this class
        results = agent.run(query, callbacks=self.callbacks)

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
            number_of_head_rows=3,
            verbose=True,
            callbacks=self.callbacks,
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
