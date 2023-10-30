# AI Assistant
An intelligent assistant.  This is a work in progress.

### Features
- ✅ AI Framework Using [LangChain](https://www.langchain.com/)
- ✅ Configuration Framework
- ✅ Console Runner (Run the LLM in a console window)
- ✅ Streamlit UI Runner (Run the LLM in a Web-UI)
- ✅ OpenAI LLM Integration
- ✅ Local LLM Integration (Llama 2- *Note: Some features may not work here yet*)
- ✅ Interaction Management (Conversations, Memory, Files, etc.)
- ✅ Chat with Documents (Upload documents on the Streamlit UI)
- ✅ Postgres Conversation / File Storage
- ✅ Voice Runner (For interactions via voice- back burner for now)

## TODO:
- ☑️ Google API Integration
- ☑️ Generic Tooling (a.k.a. on-demand tools)
- ☑️ API Discovery and Calling

# Running the UI in Docker
In order to install the assistant using Docker, you'll need the following:

- Docker ([Docker Desktop](https://www.docker.com/products/docker-desktop/) is what I use) installed and running on your computer
- Git
- A web browser
- An OpenAI Account and API key (or local models)

The steps to run the docker version is as follows:

1. Clone the assistant repo: `git clone https://github.com/aronweiler/assistant.git`
2. Edit the `.env.template` file, changing the following items:
   - `OPENAI_API_KEY` - This should be the key you generate in step 5 above.
   - `POSTGRES_`* entries can be pretty much anything you want, all of this will be local to your machine.
   - `USER_EMAIL` - Put your email in here (required for a user on the system)
   - `SOURCE_CONTROL_PROVIDER` - This is the provider you want to use if you are code reviewing files from URLs.  Can be either `GitHub` or `GitLab`
   - `SOURCE_CONTROL_URL` - Currently this only supports github or gitlab (`https://gitlab.com` or `https://github.com`)
   - `SOURCE_CONTROL_PAT` - This is a personal access token that is used to authenticate with the chosen source code provider... you can get this from the settings page of either GitHub or GitLab.
3. Rename the `.env.template` to `.env`
4. Using a command line, navigate to the directory where you cloned the code, and run `docker-compose up -d`
5. Browse to http://localhost:8500

## Updating Jarvis in Docker

*🥳 Following these update instructions **WILL NOT ERASE YOUR DATA** 🥳*
 
Run the following commands in a terminal window in the same directory as the Jarvis `docker-compose.yml`:
- `docker-compose down assistant-ui`
- `docker pull aronweiler/assistant:latest` 
  - Alternatively, you can use the version number in place of `latest`, e.g. `docker pull aronweiler/assistant:0.45`
- `docker-compose up -d assistant-ui`
- Navigate to http://localhost:8500
  
*Note: After updating you will need to re-enable/disable any tools that you previously changed on the Settings page.*


# ⚠️ WARNING ⚠️
The docker container that has the database in it is currently used primarily by me for development, so it does **not** mount a volume for the database.  
When you delete the DB docker container, **ALL OF YOUR DATA WILL BE ERASED**.

Feel free to alter this behavior on your instance, if you like.

---
Here's a lot of info on running this in Python!

# Python Prerequisits

## 1. Install the python requirements:

`pip install -r requirements.txt`

### Install Whisper and Torch (for Voice Interactions)
I'm using their github, but feel free to use the python packages.

`pip install --upgrade --no-deps --force-reinstall git+https://github.com/openai/whisper.git`

`pip3 install --force-reinstall --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu121`

## 2. Set up the database
*The database is required for conversations, file upload, user management, etc.*

### Databse-related Environment Variables

Set the following environment variables for database access:

```
POSTGRES_DB=<your desired database name>
POSTGRES_USER=<user>
POSTGRES_PASSWORD=<password>
POSTGRES_HOST=<database location>
POSTGRES_PORT=5432
```

*Note: When setting the database up, the create/migration scripts have their own settings - so you may need to adjust these.*

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

# Running the Assistant

## 4. Run the Console or Voice Assistant
Run the run.py file, with your choice of configuration.

**Example:**
`python run.py --config=configurations/console_configs/openai_config.json --logging_level=INFO`

This will allow you to interact with the AI assistant through the console.  

## Run the Streamlit UI Assistant
This is a chat bot interface that has memory, tools, and other fun stuff. 

![Streamlit UI](documentation/streamlit.png)

Run the [streamlit_ui.py](src/runners/ui/streamlit_ui.py) file with `streamlit`

Use any config that has an `ai` section, such as: `configurations/console_configs/openai_config.json`*
