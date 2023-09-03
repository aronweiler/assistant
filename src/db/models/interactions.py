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

    def update_interaction(self, session, interaction_id: UUID, interaction_summary: str, needs_summary: bool = False):
        interaction_summary = interaction_summary.strip()

        session.query(Interaction).filter(Interaction.id == interaction_id).update(
            {
                Interaction.interaction_summary: interaction_summary,
                Interaction.needs_summary: needs_summary
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
    
    def get_interaction_by_summary(
        self,
        session,
        user_id: int,
        interaction_summary: str,
        eager_load: List[InstrumentedAttribute[Any]] = []
    ):
        query = session.query(Interaction).filter(Interaction.user_id == user_id, Interaction.interaction_summary == interaction_summary)

        query = super().eager_load(query, eager_load)

        return query.first()
    
    def get_interactions_by_user_email(
        self,
        session,
        user_email: Union[str, None] = None,
        eager_load: List[InstrumentedAttribute[Any]] = []
    ) -> List[Interaction]:       
        
        if user_email is not None:
            users = Users(self.db_env_location)
            user = users.get_user_by_email(session, user_email, eager_load)
            user_id = user.id
            query = session.query(Interaction).filter(Interaction.user_id == user_id)
        else:
            query = session.query(Interaction)

        query = super().eager_load(query, eager_load)

        return query.all()
    
    def get_interactions_by_user_id(
        self,
        session,
        user_id: int,
        eager_load: List[InstrumentedAttribute[Any]] = []
    ) -> List[Interaction]:       
        
        query = session.query(Interaction).filter(Interaction.user_id == user_id)
    
        query = super().eager_load(query, eager_load)

        return query.all()