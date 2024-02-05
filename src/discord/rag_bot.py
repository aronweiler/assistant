import os
import discord
import logging
import threading
import uuid
import aiohttp

from langchain.text_splitter import RecursiveCharacterTextSplitter

# include the root directory in the path so we can import the configuration
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.ai.rag_ai import RetrievalAugmentedGenerationAI
from src.discord.memory_manager import get_conversation_memory
from src.ai.utilities.llm_helper import get_llm

from src.db.models.documents import Documents, FileModel, DocumentModel
from src.db.models.users import Users
from src.utilities.hash_utilities import calculate_sha256


class RagBot(discord.Client):
    memory_map: dict = {}
    lock = threading.Lock()

    def __init__(
        self,
        configuration,
        target_channel_name: str,
        target_collection_id: int,
        conversation_id: int,
        prompt_manager,
        user_email: str,
        status_message: str = "around with documents",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level=logging.DEBUG)
        self.configuration = configuration
        self.target_channel_name = target_channel_name
        self.target_collection_id = (
            target_collection_id if target_collection_id is not None else -1
        )
        self.conversation_id = conversation_id
        self.prompt_manager = prompt_manager
        self.user_email = user_email
        self.status_message = status_message

    async def on_ready(self):
        await self.change_presence(activity=discord.Game(name=self.status_message))

        logging.debug(f"Connected as: {self.user.name}")
        logging.debug(f"Bot ID: {self.user.id}")

    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        if message.channel.name.lower() == self.target_channel_name.lower():
            rag_ai = await self.load_rag_ai(message=message)

            await self.process_attachments(message)

            if message.content.strip() != "":
                async with message.channel.typing():
                    # Add typing indicator
                    response: str = rag_ai.query(
                        query=message.content,
                        collection_id=self.target_collection_id
                    )

                    # Sometimes the response can be over 2000 characters, so we need to split it
                    # into multiple messages, and send them one at a time
                    text_splitter = RecursiveCharacterTextSplitter(
                        separators=["\n", ".", "?", "!"],
                        chunk_size=1000,
                        chunk_overlap=0,
                        length_function=len,
                    )

                    responses = text_splitter.split_text(response)

                    for rsp in responses:
                        await message.channel.send(rsp)

    async def process_attachments(self, message):
        if len(message.attachments) > 0:
            await message.channel.send(
                "Processing attachments... (this may take a minute)"
            )

            root_temp_dir = "temp/" + str(uuid.uuid4())
            uploaded_file_paths = []
            for attachment in message.attachments:
                logging.debug(f"Downloading file from {attachment.url}")
                # Download the file
                file_path = os.path.join(root_temp_dir, attachment.filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # Download the file from the URL
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as resp:
                        if resp.status != 200:
                            raise aiohttp.ClientException(
                                f"Error downloading file from {attachment.url}"
                            )
                        data = await resp.read()

                        with open(file_path, "wb") as f:
                            f.write(data)

                uploaded_file_paths.append(file_path)

                # Process the files
            await self.load_files(
                uploaded_file_paths=uploaded_file_paths,
                root_temp_dir=root_temp_dir,
                message=message,
            )

    async def load_rag_ai(self, message) -> RetrievalAugmentedGenerationAI:
        """Loads the AI from the configuration"""
        llm = get_llm(
            model_configuration=self.configuration["jarvis_ai"]["model_configuration"]
        )
        memory = await get_conversation_memory(llm=llm, message=message)
        return RetrievalAugmentedGenerationAI(
            configuration=self.configuration,
            conversation_id=self.conversation_id,
            prompt_manager=self.prompt_manager,
            streaming=False,
            user_email=self.user_email,
            override_memory=memory,
        )

    async def load_files(self, uploaded_file_paths, root_temp_dir, message):
        documents_helper = Documents()
        user_id = Users().get_user_by_email(self.user_email).id
        logging.info(f"Processing {len(uploaded_file_paths)} files...")
        # First see if there are any files we can't load
        files = []
        for uploaded_file_path in uploaded_file_paths:
            # Get the file name
            file_name = (
                uploaded_file_path.replace(root_temp_dir, "").strip("/").strip("\\")
            )

            logging.info(f"Verifying {uploaded_file_path}...")

            # See if it exists in this collection
            existing_file = documents_helper.get_file_by_name(
                file_name, self.target_collection_id
            )

            if existing_file:
                await message.channel.send(
                    f"File '{file_name}' already exists, and overwrite is not enabled.  Ignoring..."
                )
                logging.warning(
                    f"File '{file_name}' already exists, and overwrite is not enabled"
                )
                logging.debug(f"Deleting temp file: {uploaded_file_path}")
                os.remove(uploaded_file_path)

                continue

            # Read the file
            with open(uploaded_file_path, "rb") as file:
                file_data = file.read()

            # Start off with the default file classification
            file_classification = "Document"

            # Override the classification if necessary
            IMAGE_TYPES = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"]
            # Get the file extension
            file_extension = os.path.splitext(file_name)[1]
            # Check to see if it's an image
            if file_extension in IMAGE_TYPES:
                # It's an image, reclassify it
                file_classification = "Image"

            # Create the file
            logging.info(f"Creating file '{file_name}'...")
            file = documents_helper.create_file(
                FileModel(
                    user_id=user_id,
                    collection_id=self.target_collection_id,
                    file_name=file_name,
                    file_hash=calculate_sha256(uploaded_file_path),
                    file_classification=file_classification,
                ),
                file_data,
            )
            files.append(file)

        if not files or len(files) == 0:
            logging.warning("No files to ingest")
            await message.channel.send(
                "It looks like I couldn't split (or read) any of the files that you uploaded."
            )
            return

        logging.info("Splitting documents...")

        is_code = False

        # Pass the root temp dir to the ingestion function
        documents = load_and_split_documents(
            document_directory=root_temp_dir,
            split_documents=True,
            is_code=is_code,
            chunk_size=500,
            chunk_overlap=50,
        )

        if not documents or len(documents) == 0:
            logging.warning("No documents to ingest")
            return

        logging.info(f"Saving {len(documents)} document chunks...")

        # For each document, create the file if it doesn't exist and then the document chunks
        for document in documents:
            # Get the file name without the root_temp_dir (preserving any subdirectories)
            file_name = (
                document.metadata["filename"].replace(root_temp_dir, "").strip("/")
            )

            # Get the file reference
            file = next((f for f in files if f.file_name == file_name), None)

            if not file:
                logging.error(
                    f"Could not find file '{file_name}' in the database after uploading"
                )
                break

            # Create the document chunks
            logging.info(f"Inserting document chunk for file '{file_name}'...")
            documents_helper.store_document(
                DocumentModel(
                    collection_id=self.target_collection_id,
                    file_id=file.id,
                    user_id=user_id,
                    document_text=document.page_content,
                    document_text_summary="",
                    document_text_has_summary=False,
                    additional_metadata=document.metadata,
                    document_name=document.metadata["filename"],
                )
            )

        logging.info(
            f"Successfully ingested {len(documents)} document chunks from {len(files)} files"
        )

        await message.channel.send(
            f"Successfully ingested {len(documents)} document chunks from {len(files)} files"
        )
