from src.db.database.models import Interaction


class InteractionModel:
    def __init__(
        self,
        interaction_summary,
        needs_summary,
        last_selected_collection_id,
        user_id,
        id=None,
        is_deleted=False,
        record_created=None,
    ):
        self.id = id
        self.record_created = record_created
        self.interaction_summary = interaction_summary
        self.needs_summary = needs_summary
        self.last_selected_collection_id = last_selected_collection_id
        self.user_id = user_id
        self.is_deleted = is_deleted

    def to_database_model(self):
        return Interaction(
            id=self.id,
            record_created=self.record_created,
            interaction_summary=self.interaction_summary,
            needs_summary=self.needs_summary,
            last_selected_collection_id=self.last_selected_collection_id,
            user_id=self.user_id,
            is_deleted=self.is_deleted,
        )

    @classmethod
    def from_database_model(cls, db_interaction):
        if db_interaction is None:
            return None
        
        return cls(
            id=db_interaction.id,
            record_created=db_interaction.record_created,
            interaction_summary=db_interaction.interaction_summary,
            needs_summary=db_interaction.needs_summary,
            last_selected_collection_id=db_interaction.last_selected_collection_id,
            user_id=db_interaction.user_id,
            is_deleted=db_interaction.is_deleted,
        )
