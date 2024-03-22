from src.shared.database.schema.tables import (
    SupportedSourceControlProvider,
    SourceControlProvider,
)


class SupportedSourceControlProviderModel:
    def __init__(self, name, id=None):
        self.id = id
        self.name = name

    def to_database_model(self):
        return SupportedSourceControlProvider(id=self.id, name=self.name)

    @classmethod
    def from_database_model(cls, db_model):
        return cls(id=db_model.id, name=db_model.name)


class SourceControlProviderModel:
    def __init__(
        self,
        user_id,
        supported_source_control_provider_id,
        source_control_provider_name,
        source_control_provider_url,
        requires_authentication,
        source_control_access_token,        
        last_modified=None,
        id=None,
    ):
        self.id = id
        self.user_id = user_id
        self.supported_source_control_provider_id = supported_source_control_provider_id
        self.source_control_provider_name = source_control_provider_name
        self.source_control_provider_url = source_control_provider_url
        self.requires_authentication = requires_authentication
        self.source_control_access_token = source_control_access_token
        self.last_modified = last_modified

    def to_database_model(self):
        return SourceControlProvider(
            id=self.id,
            user_id=self.user_id,
            supported_source_control_provider_id=self.supported_source_control_provider_id,
            source_control_provider_name=self.source_control_provider_name,
            source_control_provider_url=self.source_control_provider_url,
            requires_authentication=self.requires_authentication,
            source_control_access_token=self.source_control_access_token,
            last_modified=self.last_modified,
        )

    @classmethod
    def from_database_model(cls, db_model):
        return cls(
            id=db_model.id,
            user_id=db_model.user_id,
            supported_source_control_provider_id=db_model.supported_source_control_provider_id,
            source_control_provider_name=db_model.source_control_provider_name,
            source_control_provider_url=db_model.source_control_provider_url,
            requires_authentication=db_model.requires_authentication,
            source_control_access_token=db_model.source_control_access_token,
            last_modified=db_model.last_modified,
        )
