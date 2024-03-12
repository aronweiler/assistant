import openai
import os
# from dotenv import load_dotenv
#from ai.open_ai.tools.tool_wrapper import OpenAIToolWrapper


def get_openai_api_key():    
    openai.api_key = os.environ.get("OPENAI_API_KEY")

    return openai.api_key