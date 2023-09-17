import io
from io import IOBase
import os
import logging
import json
from typing import Any, List, Optional, Union

from langchain.agents import AgentType

from langchain.agents.agent import AgentExecutor
from langchain.agents.agent_toolkits.pandas.base import create_pandas_dataframe_agent
from langchain.schema.language_model import BaseLanguageModel

from src.configuration.assistant_configuration import Destination

from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_llm, get_prompt
from src.ai.system_info import get_system_information
from src.ai.destination_route import DestinationRoute
from src.ai.system_info import get_system_information
from src.ai.destinations.destination_base import DestinationBase
from src.ai.callbacks.token_management_callback import TokenManagementCallbackHandler
from src.ai.callbacks.agent_callback import AgentCallback

from src.tools.documents.document_tool import DocumentTool
from src.db.models.db_file_reader import DBFileReader
from src.db.models.domain.file_model import FileModel


class SpreadsheetsAI(DestinationBase):
    """A spreadsheet-using AI that uses an LLM to generate responses"""

    excel_types = [".xls", ".xlsx", ".ods"]

    def __init__(
        self,
        destination: Destination,
        interaction_id: int,
        user_email: str,
        streaming: bool = False,
    ):
        self.destination = destination

        self.agent_callback = AgentCallback()
        self.token_management_handler = TokenManagementCallbackHandler()

        self.llm = get_llm(
            destination.model_configuration,
            callbacks=[self.token_management_handler],
            tags=["spreadsheets"],
            streaming=streaming,
        )

        self.interaction_manager = InteractionManager(
            interaction_id,
            user_email,
            self.llm,
            destination.model_configuration.max_conversation_history_tokens,
        )

    def run(
        self,
        input: str,
        collection_id: str = None,
        llm_callbacks: list = [],
        agent_callbacks: list = [],
        kwargs: dict = {},
    ):
        self.interaction_manager.collection_id = collection_id
        self.interaction_manager.tool_kwargs = kwargs

        # Get a DBFileReader for each 'Spreadsheet' classified file in the collection
        files = self.interaction_manager.documents_helper.get_files_in_collection(
            collection_id=collection_id
        )
        spreadsheet_files = [f for f in files if f.file_classification == "Spreadsheet"]        

        self.agent = self.create_csv_agent(
            llm=self.llm,
            files=spreadsheet_files,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,            
        )

        # Maybe not needed...
        # rephrased_input = self.rephrase_query_to_standalone(input)

        results = self.agent.run(input)
        print(results)

        # Adding this after the run so that the agent can't see it in the history
        self.interaction_manager.conversation_token_buffer_memory.chat_memory.add_user_message(
            input
        )

        self.interaction_manager.conversation_token_buffer_memory.chat_memory.add_ai_message(
            results
        )

        return results

    def create_csv_agent(
        self,
        llm: BaseLanguageModel,
        files: List[FileModel],
        pandas_kwargs: Optional[dict] = None,
        **kwargs: Any,
    ) -> AgentExecutor:
        """Create csv agent by loading to a dataframe and using pandas agent."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas package not found, please install with `pip install pandas`"
            )

        _kwargs = pandas_kwargs or {}
        df = []
        
        for file in files:
            # Read in the file from the database
            reader = io.BytesIO(file.file_data)
            # Check to see if the file extension is in the excel types
            file_extension = os.path.splitext(file.file_name)[1]

            if file_extension in self.excel_types:
                # If it is, read it in as an excel file
                for sheet in pd.ExcelFile(reader, **_kwargs).sheet_names:
                    df.append(pd.read_excel(reader, sheet_name=sheet, **_kwargs))
                    #
                #df.append()
                #df.append(pd.read_excel(reader, **_kwargs))
            else:            
                df.append(pd.read_csv(filepath_or_buffer=reader, on_bad_lines='skip', encoding='ISO-8859-1', **_kwargs))
        
        return create_pandas_dataframe_agent(llm=llm, df=df, include_df_in_prompt=False, **kwargs)

    def rephrase_query_to_standalone(self, query):
        # Rephrase the query so that it is stand-alone
        # Use the llm to rephrase, adding in the conversation memory for context
        rephrase_results = self.llm.predict(
            get_prompt(
                self.destination.model_configuration.llm_type, "REPHRASE_TEMPLATE"
            ).format(
                input=query,
                chat_history="\n".join(
                    [
                        f"{'AI' if m.type == 'ai' else f'{self.interaction_manager.user_name} ({self.interaction_manager.user_email})'}: {m.content}"
                        for m in self.interaction_manager.conversation_token_buffer_memory.buffer_as_messages[
                            -8:
                        ]
                    ]
                ),
                system_information=get_system_information(
                    self.interaction_manager.user_location
                ),
                user_name=self.interaction_manager.user_name,
                user_email=self.interaction_manager.user_email,
                loaded_documents="\n".join(
                    self.interaction_manager.get_loaded_documents_for_reference()
                ),
            )
        )

        return rephrase_results
