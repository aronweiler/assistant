from typing import List, Any
from uuid import UUID
from sqlalchemy.orm.attributes import InstrumentedAttribute

from src.db.database.models import Interaction
from src.db.models.vector_database import VectorDatabase
from src.db.models.domain.interaction_model import InteractionModel


class Interactions(VectorDatabase):
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

    def update_interaction_summary(
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

    def update_interaction_collection(
        self,
        interaction_id: UUID,
        last_selected_collection_id: int,
    ):
        with self.session_context(self.Session()) as session:
            session.query(Interaction).filter(Interaction.id == interaction_id).update(
                {
                    Interaction.last_selected_collection_id: last_selected_collection_id,
                }
            )

            session.commit()

    def get_interaction(
        self, id: UUID
    ) -> InteractionModel:
        with self.session_context(self.Session()) as session:
            query = session.query(
                Interaction.interaction_summary,
                Interaction.needs_summary,
                Interaction.last_selected_collection_id,
                Interaction.user_id,
                Interaction.id,
                Interaction.is_deleted,
                Interaction.record_created,
            ).filter(Interaction.id == id)

            return InteractionModel.from_database_model(query.first())

    def get_interactions_by_user_id(
        self, user_id: int
    ) -> List[InteractionModel]:
        with self.session_context(self.Session()) as session:
            query = session.query(Interaction.interaction_summary,
                Interaction.needs_summary,
                Interaction.last_selected_collection_id,
                Interaction.user_id,
                Interaction.id,
                Interaction.is_deleted,
                Interaction.record_created,).filter(
                Interaction.user_id == user_id, Interaction.is_deleted == False
            )

            return [InteractionModel.from_database_model(i) for i in query.all()]

    def delete_interaction(self, interaction_id: UUID) -> None:
        with self.session_context(self.Session()) as session:
            session.query(Interaction).filter(Interaction.id == interaction_id).update(
                {Interaction.is_deleted: True}
            )
            session.commit()
