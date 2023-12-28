from src.db.database.tables import Conversation


class ConversationModel:
    def __init__(
        self,
        conversation_summary,
        needs_summary,
        last_selected_collection_id,        
        user_id,
        last_selected_code_repo=None,
        id=None,
        is_deleted=False,
        record_created=None,
    ):
        self.id = id
        self.record_created = record_created
        self.conversation_summary = conversation_summary
        self.needs_summary = needs_summary
        self.last_selected_collection_id = last_selected_collection_id
        self.last_selected_code_repo = last_selected_code_repo
        self.user_id = user_id
        self.is_deleted = is_deleted

    def to_database_model(self):
        return Conversation(
            id=self.id,
            record_created=self.record_created,
            conversation_summary=self.conversation_summary,
            needs_summary=self.needs_summary,
            last_selected_collection_id=self.last_selected_collection_id,
            last_selected_code_repo=self.last_selected_code_repo,
            user_id=self.user_id,
            is_deleted=self.is_deleted,
        )

    @classmethod
    def from_database_model(cls, db_conversation):
        if db_conversation is None:
            return None
        
        return cls(
            id=db_conversation.id,
            record_created=db_conversation.record_created,
            conversation_summary=db_conversation.conversation_summary,
            needs_summary=db_conversation.needs_summary,
            last_selected_collection_id=db_conversation.last_selected_collection_id,
            last_selected_code_repo=db_conversation.last_selected_code_repo,
            user_id=db_conversation.user_id,
            is_deleted=db_conversation.is_deleted,
        )
