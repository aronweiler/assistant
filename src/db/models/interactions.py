from typing import List, Any
from uuid import UUID
from sqlalchemy.orm.attributes import InstrumentedAttribute

from db.database.models import Interaction
from db.models.vector_database import VectorDatabase
from db.models.domain.interaction_model import InteractionModel


class Interactions(VectorDatabase):
    def __init__(self, db_env_location):
        super().__init__(db_env_location)

        self.db_env_location = db_env_location

    def create_interaction(
        self, id: UUID, interaction_summary: str, user_id: int
    ) -> InteractionModel:
        with self.session_context(self.Session()) as session:
            interaction_summary = interaction_summary.strip()

            interaction = Interaction(
                id=id, interaction_summary=interaction_summary, user_id=user_id
            )

            session.add(interaction)
            session.commit()

            return InteractionModel.from_database_model(interaction)

    def update_interaction(
        self,
        interaction_id: UUID,
        interaction_summary: str,
        needs_summary: bool = False,
    ):
        with self.session_context(self.Session()) as session:
            interaction_summary = interaction_summary.strip()

            session.query(Interaction).filter(Interaction.id == interaction_id).update(
                {
                    Interaction.interaction_summary: interaction_summary,
                    Interaction.needs_summary: needs_summary,
                }
            )

            session.commit()

    def get_interaction(
        self, id: UUID, eager_load: List[InstrumentedAttribute[Any]] = []
    ) -> InteractionModel:
        with self.session_context(self.Session()) as session:
            query = session.query(Interaction).filter(Interaction.id == id)

            query = super().eager_load(query, eager_load)

            return InteractionModel.from_database_model(query.first())

    def get_interactions_by_user_id(
        self, user_id: int, eager_load: List[InstrumentedAttribute[Any]] = []
    ) -> List[InteractionModel]:
        with self.session_context(self.Session()) as session:
            query = session.query(Interaction).filter(Interaction.user_id == user_id)

            query = super().eager_load(query, eager_load)

            return [InteractionModel.from_database_model(i) for i in query.all()]
