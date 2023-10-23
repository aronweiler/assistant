import subprocess
import os

from src.db.models.documents import Documents
from src.ai.interactions.interaction_manager import InteractionManager

# TODO: Make this configurable
LLAVA_CMD = '{llava_exe} -m H:\LLM\llava-v1.5-7b\ggml-model-q5_k.gguf --mmproj H:\LLM\llava-v1.5-7b\mmproj-model-f16.gguf --temp 0.1 -ngl 50 -p "{prompt}" --image "{image_path}"'


class LlavaTool:
    def __init__(self, llava_path: str) -> None:
        self.llava_path = llava_path
        self.document_helper = Documents()

    def query_image(self, target_file_id: int, query: str) -> str:
        """Queries the image with the given query

        Args:
            target_file_id (int): The target file ID
            query (str): The query to run

        Returns:
            str: The result of the query
        """
        # First, get the image from the database and save it to a temporary file (if not already done)
        file = self.document_helper.get_file(target_file_id)

        # Write the file data to a temporary file
        temp_file_path = f"/temp_images/{file.file_name}"

        # If the file does not exist, create it.
        if not os.path.exists(temp_file_path):
            # Make sure the directory exists
            os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)

            with open(temp_file_path, "wb") as f:
                f.write(file.file_data)

        # Now, run the query
        command = LLAVA_CMD.format(
            llava_exe=self.llava_path, prompt=query, image_path=temp_file_path
        )

        # Execute the command
        result = subprocess.run(command, shell=True, capture_output=True)

        return result.stdout.decode("utf-8")
