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
        "llama2": "llama2_prompts",
        "openai": "openai_prompts",
    }

    def __init__(self, llm_type: str = "openai"):
        self.llm_type = llm_type
        self.prompt_category = {}
        self.load_prompts()

    @staticmethod
    def get_module_name_from_category(category: str) -> str:
        return category

    def get_prompt_by_category_and_name(self, category: str, prompt_name: str) -> str:
        module_name = self.get_module_name_from_category(category=category)
        prompt = getattr(self.prompt_category[module_name], prompt_name)
        return prompt

    def get_prompt_by_template_name(self, prompt_name: str) -> str:
        # Find the prompt_name in the prompt category dictionary
        for category, prompt in self.prompt_category.items():
            if hasattr(prompt, prompt_name):
                return getattr(prompt, prompt_name)

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

    print(
        pm.get_prompt_by_category_and_name(
            category="conversational_prompts", prompt_name="CONVERSATIONAL_PROMPT"
        )
    )
