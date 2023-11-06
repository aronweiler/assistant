from src.db.database.models import Conversation
from src.db.models.domain.conversation_role_type import ConversationRoleType


class ConversationModel:
    def __init__(
        self,
        interaction_id,
        conversation_text,
        user_id,
        conversation_role_type: ConversationRoleType,
        id=None,
        record_created=None,
        additional_metadata=None,
        exception=None,
        is_deleted=False,
    ):
        self.id = id
        self.record_created = record_created
        self.interaction_id = interaction_id
        self.conversation_text = conversation_text
        self.user_id = user_id
        self.additional_metadata = additional_metadata
        self.exception = exception
        self.is_deleted = is_deleted
        self.conversation_role_type = conversation_role_type

    def to_database_model(self):
        return Conversation(
            id=self.id,
            record_created=self.record_created,
            interaction_id=self.interaction_id,
            conversation_role_type_id=self.conversation_role_type.value,
            conversation_text=self.conversation_text,
            user_id=self.user_id,
            additional_metadata=self.additional_metadata,
            exception=self.exception,
            is_deleted=self.is_deleted,
        )

    @classmethod
    def from_database_model(cls, db_conversation):
        if db_conversation is None:
            return None

        return cls(
            id=db_conversation.id,
            record_created=db_conversation.record_created,
            interaction_id=db_conversation.interaction_id,
            conversation_role_type=ConversationRoleType(
                db_conversation.conversation_role_type_id
            ),
            conversation_text=db_conversation.conversation_text,
            user_id=db_conversation.user_id,
            additional_metadata=db_conversation.additional_metadata,
            exception=db_conversation.exception,
            is_deleted=db_conversation.is_deleted,
        )
