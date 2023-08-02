# Long-Term Memory
*Note: This module has its own dependencies and [requirements.txt](requirements.txt)*

The objective of this module is to allow an LLM to maintain a long-term memory of a sort by storing information in a database.

## Settings information
Over time, the LLM may be asked to change its settings (through the settings tool), and we can track the changes here, loading the active settings for things like:
- Initial prompt(s)
- Voice settings, such as voice speed, personality, etc.
- ... 

## Conversation information
Conversation information pertains to any information gathered or cleaned from conversations with a user.  Conversation text is usually associated with an action taken by the LLM, whether that uses any of the other data stored or not.

There are different types of conversation-related information that we might store:
- User query
- AI response
- Tools used
- ...

## Reference information
Reference information refers to any auxiliary or external information that might be pre-loaded or loaded on command.  

Reference information can include:
- Reference documents such as manuals or product documentation
- Specifications, such as API descriptions
- ...

# Why?
There are a number of goals for adding storage that the LLM can access and associating the data with conversations (a.k.a. creating a memory):
- It will allow the LLM to recall actions it took related to user input, and then see the outcome of its actions (retrieve memories- what worked, what didn't)
- The LLM can use the data store for the various tools it will employ- for instance, if we have and API specification stored for an application, it can be referenced by the model when interacting with the specified API.
- The LLM can look up other documents that might not have been available to the model during training.
- ...


# Setup

### 1. Install requirements:

`pip install -r requirements.txt`

### 2. Using PGVector docker image:

Pull and run the pgvector docker file, following instructions here: [PGVector GitHub](https://github.com/pgvector/pgvector/tree/master#docker)

You can also run my docker-compose file via `docker-compose up -d` from the long_term folder.

### 3. Enable the pgvector extension

Create a database, and run the following SQL script on that database:
``` sql
CREATE EXTENSION vector;
```

### 4. Database migrations:

#### Alembic Setup:
To use Alembic for migrations, you'll need to set up a directory structure for Alembic to manage the migrations. First, create a directory named migrations in your project root. Then, initialize Alembic inside this directory:

``` bash
alembic init migrations
```
This will create an alembic.ini file and a versions directory inside the migrations directory.  The versions directory is required, but the alembic.ini is not!

#### SIMPLE Setup:
1. Run [generate_migration.py](generate_migration.py)
2. Run [run_migration.py](run_migration.py)


### More Details

#### Configure Alembic:
Edit the alembic.ini file to specify your database connection details.

`sqlalchemy.url = postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}`

These environment variables should be loaded by the python environment- see [vector_database.py](vector_database.py)

#### Define Database Models:
In the models.py file (you can create this in the migrations directory), define your database models using SQLAlchemy's declarative syntax.

``` python
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class YourModel(Base):
    __tablename__ = 'your_table_name'

    id = Column(Integer, primary_key=True)
    column1 = Column(String)
    column2 = Column(String)
    # Add more columns as needed
```

#### Generate the Initial Migration: 

With Alembic configured, you can generate an initial migration for your database schema using the following command:

``` bash
alembic revision --autogenerate -m "initial migration"
```

This command will compare the current state of your models defined in models.py with the current state of the database and create a migration script that reflects the changes required to bring the database schema in sync with your models.

#### Apply Migrations: 
Once the initial migration script is generated, you can apply it to your database to create the tables:

``` bash
alembic upgrade head
```

This will create the users and conversations tables in your database.

#### Creating Additional Migrations: 
As you make changes to your models (e.g., add new columns, alter existing columns), you can generate additional migrations using `alembic revision --autogenerate -m "migration_name"` and then apply them using `alembic upgrade head`.