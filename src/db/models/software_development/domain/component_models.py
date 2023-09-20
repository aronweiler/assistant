from src.db.database.models import (
    Component,
    ComponentDataHandling,
    ComponentInteraction,
    ComponentDependency,
)


class ComponentModel:
    def __init__(self, id, name, purpose):
        self.id = id
        self.name = name
        self.purpose = purpose

    def to_database_model(self):
        return Component(id=self.id, name=self.name, purpose=self.purpose)

    @classmethod
    def from_database_model(cls, db_component):
        if db_component is None:
            return None

        return cls(
            id=db_component.id, name=db_component.name, purpose=db_component.purpose
        )


class ComponentDataHandlingModel:
    def __init__(self, id, component_id, data_name, data_type, description):
        self.id = id
        self.component_id = component_id
        self.data_name = data_name
        self.data_type = data_type
        self.description = description

    def to_database_model(self):
        return ComponentDataHandling(
            id=self.id,
            component_id=self.component_id,
            data_name=self.data_name,
            data_type=self.data_type,
            description=self.description,
        )

    @classmethod
    def from_database_model(cls, db_component_data_handling):
        if db_component_data_handling is None:
            return None

        return cls(
            id=db_component_data_handling.id,
            component_id=db_component_data_handling.component_id,
            data_name=db_component_data_handling.data_name,
            data_type=db_component_data_handling.data_type,
            description=db_component_data_handling.description,
        )


class ComponentInteractionModel:
    def __init__(self, id, component_id, interacts_with, description):
        self.id = id
        self.component_id = component_id
        self.interacts_with = interacts_with
        self.description = description

    def to_database_model(self):
        return ComponentInteraction(
            id=self.id,
            component_id=self.component_id,
            interacts_with=self.interacts_with,
            description=self.description,
        )

    @classmethod
    def from_database_model(cls, db_component_interaction):
        if db_component_interaction is None:
            return None

        return cls(
            id=db_component_interaction.id,
            component_id=db_component_interaction.component_id,
            interacts_with=db_component_interaction.interacts_with,
            description=db_component_interaction.description,
        )


class ComponentDependencyModel:
    def __init__(self, id, component_id, dependency_name, description):
        self.id = id
        self.component_id = component_id
        self.dependency_name = dependency_name
        self.description = description

    def to_database_model(self):
        return ComponentDependency(
            id=self.id,
            component_id=self.component_id,
            dependency_name=self.dependency_name,
            description=self.description,
        )

    @classmethod
    def from_database_model(cls, db_component_dependency):
        if db_component_dependency is None:
            return None

        return cls(
            id=db_component_dependency.id,
            component_id=db_component_dependency.component_id,
            dependency_name=db_component_dependency.dependency_name,
            description=db_component_dependency.description,
        )
