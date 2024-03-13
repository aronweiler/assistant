from src.shared.database.schema.tables import ConversationMessage
from src.shared.database.models.domain.conversation_role_type import ConversationRoleType


class ConversationMessageModel:
    def __init__(
        self,
        conversation_id,
        message_text,
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
        self.conversation_id = conversation_id
        self.message_text = message_text
        self.user_id = user_id
        self.additional_metadata = additional_metadata
        self.exception = exception
        self.is_deleted = is_deleted
        self.conversation_role_type = conversation_role_type

    def to_database_model(self):
        return ConversationMessage(
            id=self.id,
            record_created=self.record_created,
            conversation_id=self.conversation_id,
            conversation_role_type_id=self.conversation_role_type.value,
            message_text=self.message_text,
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
            conversation_id=db_conversation.conversation_id,
            conversation_role_type=ConversationRoleType(
                db_conversation.conversation_role_type_id
            ),
            message_text=db_conversation.message_text,
            user_id=db_conversation.user_id,
            additional_metadata=db_conversation.additional_metadata,
            exception=db_conversation.exception,
            is_deleted=db_conversation.is_deleted,
        )
