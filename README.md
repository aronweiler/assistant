# AI Assistant
An intelligent assistant.  This is a work in progress.

### Features
- ✅ Runner / AI Framework
- ✅ Tool Framework
- ✅ Configuration Framework
- ✅ Console Runner
- ✅ OpenAI LLM Integration
- ✅ Memory Retrieval
- ✅ Conversation Manager
- ✅ Memory Storage (This is really exciting!)
- ✅ Voice Runner
- ✅ BASIC Streamlit UI
- ☑️ Google API Integration
- ☑️ Generic Tooling (a.k.a. on-demand tools)
- ☑️ API Discovery and Calling

# Running the Assistant

## 1. Install the python requirements:

`pip install -r requirements.txt`

## 2. Set up the database
*The database is required for some of the more advanced features, like conversations, and eventually things like documents, advanced tooling, etc.*
### - Run the PGVector (postgres) docker image:

Pull and run the PGVector docker file, following instructions here: [PGVector GitHub](https://github.com/pgvector/pgvector/tree/master#docker)

You can also run my docker-compose file via `docker-compose up -d` from the database folder.

### - Create the database
After creating and running the database docker image, you need to create the actual database.

Run the [create_database.py](src\db\database\create_database.py) python script.

This creates the database...  but for some reason the vector extension is not create.

Connect to the new database, and run: `CREATE EXTENSION IF NOT EXISTS vector;`

### - Set up database migrations:
Migrations make it easy to add/change/remove things from the database when you already have data in there. 

#### - Alembic for migrations setup:
To use Alembic for migrations, you'll need to set up a directory structure for Alembic to manage the migrations. First, create a directory named migrations in your project root. Then, initialize Alembic inside this directory:

``` bash
alembic init migrations
```
This will create an alembic.ini file and a versions directory inside the migrations directory.  The versions directory is required, but the alembic.ini is not!

#### - Running migrations:
1. Run [generate_migration.py](generate_migration.py)
   - This will generate the migrations that contain the changes (or just the initial database) between the current DB and any modifications that have been made to the DB models in code.
2. Run [run_migration.py](run_migration.py)
   - This will push those changes to the database, safely migrating your data.

### More info on the database
See [Memory](src\db\readme.md)

## 3. Configure the assistant
Currently, only the [console_ai_assistant](configurations\console_configs\console_ai_assistant.json) is supported.  Take a look at that configuration file to get a flavor for what future implementations will look like.

Modify the [console_ai_assistant](configurations\console_configs\console_ai_assistant.json) to suit your needs.

## 4. Run the Console or Voice Assistant
Run the run.py file, with your choice of configuration.

**Example:**
`python run.py --config=configurations/console_configs/console_ai.json --logging_level=INFO`

This should allow you to interact with the AI assistant through the console.  

## Run the Streamlit UI Assistant
Run the [streamlit_ui.py](src/runners/ui/streamlit_ui.py) file with `streamlit`

**Example:**
`streamlit run src/runners/ui/streamlit_ui.py`

*Note- this approach currently relies on the `OPENAI_API_KEY` and `ASSISTANT_CONFIG_PATH` environment variables.  Make sure they are set.

Use any config that has an `ai` section, such as: `configurations/console_configs/console_ai.json`*