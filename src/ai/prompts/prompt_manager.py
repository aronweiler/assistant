import importlib
import os
import pathlib
import sys

# sys.path.append(
#     os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
# )

sys.path.append(os.path.abspath(os.path.dirname(__file__)))


class PromptManager:
    LLM_TYPE_TO_DIR_MAP = {
        "llama2": "llama2",
        "openai": "openai",
    }

    def __init__(self, llm_type: str):
        self.llm_type = llm_type
        self.prompt_category = {}
        self.load_prompts()

    @staticmethod
    def get_module_name_from_category(category: str) -> str:
        return category

    def get_prompt(self, category: str, prompt_name: str) -> str:
        module_name = self.get_module_name_from_category(category=category)
        prompt = getattr(self.prompt_category[module_name], prompt_name)
        return prompt

    def load_prompts(self) -> None:
        path_to_current_file_directory = pathlib.Path(__file__).parent.absolute()

        dir_name = PromptManager.LLM_TYPE_TO_DIR_MAP[self.llm_type]

        sys.path.append(
            os.path.abspath(os.path.join(os.path.dirname(__file__), dir_name))
        )

        model_dir = path_to_current_file_directory / dir_name
        files = [f for f in os.listdir(model_dir)]

        for file in files:
            module_name = os.path.splitext(file)[0]
            module = importlib.import_module(module_name)
            self.prompt_category[module_name] = module


if __name__ == "__main__":
    pm = PromptManager(llm_type="openai")

    print(pm.get_prompt(category="conversational", prompt_name="CONVERSATIONAL_PROMPT"))
