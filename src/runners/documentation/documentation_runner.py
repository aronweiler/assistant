import os
import openai
from langchain.chat_models.openai import ChatOpenAI


class DocumentationRunner:
    def summarize_document(self, document_data: str, file_path: str) -> dict:
        llm = self._get_openai_llm()

        result = llm.predict(
            f"Please write a detailed summary of the following code:\n\n```\n{document_data}\n```\n\nAI: Sure, here is a detailed summary of the provided code:\n"
        )

        return {"file_path": file_path, "summary": result}

    def combine_summaries(self, document_summaries: list) -> str:
        llm = self._get_openai_llm()

        summaries = "\n\n".join(
            [
                f"File: {summary['file_path']}\n {summary['summary']}"
                for summary in document_summaries
            ]
        )

        prompt = f"Please combine the following summaries of code files into a comprehensive description of the software.  Please use Markdown in your output.\n\n{summaries}\n\nAI: Sure, here is a comprehensive description of the software in Markdown:\n"

        result = llm.predict(prompt)

        return result

    def _get_openai_llm(self):
        llm = ChatOpenAI(
            model="gpt-4-1106-preview",
            temperature=0,
            max_retries=3,
            max_tokens=4096,
            openai_api_key=self._get_openai_api_key(),
            verbose=True,
            model_kwargs={"seed": 500},
        )

        return llm

    def _get_openai_api_key(self):
        openai.api_key = os.environ.get("OPENAI_API_KEY")

        return openai.api_key

    def run(self, path: str, file_extension: str = None):
        summary_results = []

        if os.path.isdir(path):
            if not file_extension:
                raise ValueError("File extension must be provided for directories")
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith(file_extension):
                        file_path = os.path.join(root, file)
                        with open(file_path, "r") as f:
                            document_data = f.read()
                            if document_data.strip() != "":
                                summary = self.summarize_document(document_data=document_data, file_path=file_path)
                                summary_results.append(summary)
        elif os.path.isfile(path):
            with open(path, "r") as f:
                document_data = f.read()
                if document_data.strip() != "":
                    summary = self.summarize_document(document_data)
                    summary_results.append(summary)
        else:
            raise ValueError("The path provided does not exist")

        combined_summary = self.combine_summaries(summary_results)

        print(combined_summary)


if __name__ == "__main__":
    import sys

    # Basic argument validation
    if len(sys.argv) < 2:
        print("Usage: python script.py <path> [file_extension]")
        sys.exit(1)

    path_arg = sys.argv[1]
    file_ext_arg = sys.argv[2] if len(sys.argv) > 2 else None

    runner = DocumentationRunner()
    runner.run(path_arg, file_ext_arg)
