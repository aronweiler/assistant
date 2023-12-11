import subprocess
import os

from src.db.models.documents import Documents
from src.ai.conversations.conversation_manager import ConversationManager

# TODO: Make this configurable
LLAVA_CMD = '{llava_path} -m {llava_model} --mmproj {llava_mmproj} --temp {llava_temp} -ngl {llava_gpu_layers} -p "{prompt}" --image "{image_path}"'


class LlavaTool:
    def __init__(
        self,
        llava_path: str,
        llava_model: str,
        llava_mmproj: str,
        llava_temp: float,
        llava_gpu_layers: int,
    ):
        self.document_helper = Documents()

        self.llava_path = llava_path
        self.llava_model = llava_model
        self.llava_mmproj = llava_mmproj
        self.llava_temp = llava_temp
        self.llava_gpu_layers = llava_gpu_layers

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
        temp_file_path = f"temp_images/{file.file_name}"

        # If the file does not exist, create it.
        if not os.path.exists(temp_file_path):
            # Make sure the directory exists
            os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)

            with open(temp_file_path, "wb") as f:
                f.write(self.document_helper.get_file_data(file.id))

        # Now, run the query
        command = LLAVA_CMD.format(
            llava_path=self.llava_path,
            prompt=query,
            image_path=temp_file_path,
            llava_model=self.llava_model,
            llava_mmproj=self.llava_mmproj,
            llava_temp=self.llava_temp,
            llava_gpu_layers=self.llava_gpu_layers,
        )

        # Execute the command
        result = subprocess.run(command, shell=True, capture_output=True)

        return result.stdout.decode("utf-8")
