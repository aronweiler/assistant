import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from uuid import uuid4

#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.ai.rag_ai import RetrievalAugmentedGenerationAI


class TestRetrievalAugmentedGenerationAI(unittest.TestCase):

    def setUp(self):
        self.mock_config = {'jarvis_ai': {'model_configuration': {}, 'file_ingestion_configuration': {}}}
        self.mock_prompt_manager = MagicMock()
        self.conversation_id = uuid4()
        self.user_email = 'test@example.com'

    def test_init_value_error(self):
        with self.assertRaises(ValueError):
            RetrievalAugmentedGenerationAI(configuration=None, conversation_id=None, user_email=None, prompt_manager=None)

    @patch('rag_ai.RetrievalAugmentedGenerationAI.create_agent')
    def test_query(self, mock_create_agent):
        # Mock the agent's response
        mock_create_agent.return_value = MagicMock()
        mock_create_agent.return_value.invoke.return_value = {'output': 'Test response'}

        rag_ai = RetrievalAugmentedGenerationAI(
            configuration=self.mock_config,
            conversation_id=self.conversation_id,
            user_email=self.user_email,
            prompt_manager=self.mock_prompt_manager,
            streaming=False
        )
        output = rag_ai.query('Test query')
        self.assertIn('Test response', output)

    # Add more tests here to cover other methods like run_chain, run_agent, etc.

if __name__ == '__main__':
    unittest.main()