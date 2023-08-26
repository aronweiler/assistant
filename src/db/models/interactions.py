from typing import Union, List, Any
from uuid import UUID
from sqlalchemy.orm.attributes import InstrumentedAttribute


from sqlalchemy import select

# For testing
# Add the root path to the python path so we can import the database
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from db.database.models import Interaction, Conversation, User
from db.models.vector_database import VectorDatabase
from db.models.users import Users


class Interactions(VectorDatabase):
    def __init__(self, db_env_location):
        super().__init__(db_env_location)

        self.db_env_location = db_env_location

    def create_interaction(
        self,
        session,
        id: UUID,
        interaction_summary: str,
        user_id: int
    ):
        interaction_summary = interaction_summary.strip()

        interaction = Interaction(
            id=id,
            interaction_summary=interaction_summary,
            user_id=user_id
        )

        session.add(interaction)

    def update_interaction(self, session, interaction_id: UUID, interaction_summary: str):
        interaction_summary = interaction_summary.strip()

        session.query(Interaction).filter(Interaction.id == interaction_id).update(
            {
                Interaction.interaction_summary: interaction_summary
            }
        )

        session.commit()

    def get_interaction(
        self,
        session,
        id: UUID,
        eager_load: List[InstrumentedAttribute[Any]] = []
    ):
        query = session.query(Interaction).filter(Interaction.id == id)

        query = super().eager_load(query, eager_load)

        return query.first()
    
    def get_interactions(
        self,
        session,
        user_email: Union[str, None] = None,
        eager_load: List[InstrumentedAttribute[Any]] = []
    ):       
        
        if user_email is not None:
            users = Users(self.db_env_location)
            user = users.find_user_by_email(session, user_email, eager_load)
            user_id = user.id
            query = session.query(Interaction).filter(Interaction.user_id == user_id)
        else:
            query = session.query(Interaction)

        query = super().eager_load(query, eager_load)

        return query.all()