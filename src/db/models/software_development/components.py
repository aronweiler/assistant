from typing import List

from src.db.models.vector_database import VectorDatabase
from src.db.database.models import Component as DBComponent
from src.db.database.models import ComponentDataHandling, ComponentInteraction, ComponentDependency
from src.db.models.software_development.domain.component_models import (
    ComponentModel,
    ComponentDataHandlingModel,
    ComponentInteractionModel,
    ComponentDependencyModel,
)

class Components(VectorDatabase):

    def create_component(self, name, purpose) -> ComponentModel:
        with self.session_context(self.Session()) as session:
            component = DBComponent(name=name, purpose=purpose)
            session.add(component)
            session.commit()
            return ComponentModel.from_database_model(component)
        
    def get_component(self, component_id) -> ComponentModel:
        with self.session_context(self.Session()) as session:
            component = session.query(DBComponent).filter(DBComponent.id == component_id).first()
            return ComponentModel.from_database_model(component)
        
    def get_components_by_project_id(self, project_id) -> List[ComponentModel]:
        with self.session_context(self.Session()) as session:
            components = session.query(DBComponent).filter(DBComponent.project_id == project_id).all()
            return [ComponentModel.from_database_model(c) for c in components]
        
    def update_component(self, component_id, new_name, new_purpose) -> ComponentModel:
        with self.session_context(self.Session()) as session:
            component = session.query(DBComponent).filter(DBComponent.id == component_id).first()
            component.name = new_name
            component.purpose = new_purpose
            session.commit()
            return ComponentModel.from_database_model(component)
        
    def delete_component(self, component_id) -> bool:
        with self.session_context(self.Session()) as session:
            component = session.query(DBComponent).filter(DBComponent.id == component_id).first()
            if component:
                session.delete(component)
                session.commit()
                return True
            return False
        
    def create_component_data_handling(self, component_id, data_name, data_type, description) -> ComponentDataHandlingModel:
        with self.session_context(self.Session()) as session:
            component_data_handling = ComponentDataHandling(component_id=component_id, data_name=data_name, data_type=data_type, description=description)
            session.add(component_data_handling)
            session.commit()
            return ComponentDataHandlingModel.from_database_model(component_data_handling)
        
    def get_component_data_handling(self, component_data_handling_id) -> ComponentDataHandlingModel:
        with self.session_context(self.Session()) as session:
            component_data_handling = session.query(ComponentDataHandling).filter(ComponentDataHandling.id == component_data_handling_id).first()
            return ComponentDataHandlingModel.from_database_model(component_data_handling)
        
    def get_component_data_handlings(self) -> List[ComponentDataHandlingModel]:
        with self.session_context(self.Session()) as session:
            component_data_handlings = session.query(ComponentDataHandling).all()
            return [ComponentDataHandlingModel.from_database_model(c) for c in component_data_handlings]
        
    def update_component_data_handling(self, component_data_handling_id, new_component_id, new_data_name, new_data_type, new_description) -> ComponentDataHandlingModel:
        with self.session_context(self.Session()) as session:
            component_data_handling = session.query(ComponentDataHandling).filter(ComponentDataHandling.id == component_data_handling_id).first()
            component_data_handling.component_id = new_component_id
            component_data_handling.data_name = new_data_name
            component_data_handling.data_type = new_data_type
            component_data_handling.description = new_description
            session.commit()
            return ComponentDataHandlingModel.from_database_model(component_data_handling)
        
    def delete_component_data_handling(self, component_data_handling_id) -> bool:
        with self.session_context(self.Session()) as session:
            component_data_handling = session.query(ComponentDataHandling).filter(ComponentDataHandling.id == component_data_handling_id).first()
            if component_data_handling:
                session.delete(component_data_handling)
                session.commit()
                return True
            return False
        
    def create_component_interaction(self, component_id, interacts_with, description) -> ComponentInteractionModel:
        with self.session_context(self.Session()) as session:
            component_interaction = ComponentInteraction(component_id=component_id, interacts_with=interacts_with, description=description)
            session.add(component_interaction)
            session.commit()
            return ComponentInteractionModel.from_database_model(component_interaction)
        
    def get_component_interaction(self, component_interaction_id) -> ComponentInteractionModel:
        with self.session_context(self.Session()) as session:
            component_interaction = session.query(ComponentInteraction).filter(ComponentInteraction.id == component_interaction_id).first()
            return ComponentInteractionModel.from_database_model(component_interaction)
        
    def get_component_interactions(self) -> List[ComponentInteractionModel]:
        with self.session_context(self.Session()) as session:
            component_interactions = session.query(ComponentInteraction).all()
            return [ComponentInteractionModel.from_database_model(c) for c in component_interactions]
        
    def update_component_interaction(self, component_interaction_id, new_component_id, new_interacts_with, new_description) -> ComponentInteractionModel:
        with self.session_context(self.Session()) as session:
            component_interaction = session.query(ComponentInteraction).filter(ComponentInteraction.id == component_interaction_id).first()
            component_interaction.component_id = new_component_id
            component_interaction.interacts_with = new_interacts_with
            component_interaction.description = new_description
            session.commit()
            return ComponentInteractionModel.from_database_model(component_interaction)
        
    def delete_component_interaction(self, component_interaction_id) -> bool:
        with self.session_context(self.Session()) as session:
            component_interaction = session.query(ComponentInteraction).filter(ComponentInteraction.id == component_interaction_id).first()
            if component_interaction:
                session.delete(component_interaction)
                session.commit()
                return True
            return False
        
    def create_component_dependency(self, component_id, depends_on, description) -> ComponentDependencyModel:
        with self.session_context(self.Session()) as session:
            component_dependency = ComponentDependency(component_id=component_id, depends_on=depends_on, description=description)
            session.add(component_dependency)
            session.commit()
            return ComponentDependencyModel.from_database_model(component_dependency)
        
    def get_component_dependency(self, component_dependency_id) -> ComponentDependencyModel:
        with self.session_context(self.Session()) as session:
            component_dependency = session.query(ComponentDependency).filter(ComponentDependency.id == component_dependency_id).first()
            return ComponentDependencyModel.from_database_model(component_dependency)
        
    def get_component_dependencies(self) -> List[ComponentDependencyModel]:
        with self.session_context(self.Session()) as session:
            component_dependencies = session.query(ComponentDependency).all()
            return [ComponentDependencyModel.from_database_model(c) for c in component_dependencies]
        
    def update_component_dependency(self, component_dependency_id, new_component_id, new_depends_on, new_description) -> ComponentDependencyModel:
        with self.session_context(self.Session()) as session:
            component_dependency = session.query(ComponentDependency).filter(ComponentDependency.id == component_dependency_id).first()
            component_dependency.component_id = new_component_id
            component_dependency.depends_on = new_depends_on
            component_dependency.description = new_description
            session.commit()
            return ComponentDependencyModel.from_database_model(component_dependency)
        
    def delete_component_dependency(self, component_dependency_id) -> bool:
        with self.session_context(self.Session()) as session:
            component_dependency = session.query(ComponentDependency).filter(ComponentDependency.id == component_dependency_id).first()
            if component_dependency:
                session.delete(component_dependency)
                session.commit()
                return True
            return False
        
    def get_component_data_handlings_by_component_id(self, component_id) -> List[ComponentDataHandlingModel]:
        with self.session_context(self.Session()) as session:
            component_data_handlings = session.query(ComponentDataHandling).filter(ComponentDataHandling.component_id == component_id).all()
            return [ComponentDataHandlingModel.from_database_model(c) for c in component_data_handlings]
        
    def get_component_interactions_by_component_id(self, component_id) -> List[ComponentInteractionModel]:
        with self.session_context(self.Session()) as session:
            component_interactions = session.query(ComponentInteraction).filter(ComponentInteraction.component_id == component_id).all()
            return [ComponentInteractionModel.from_database_model(c) for c in component_interactions]
        
    def get_component_dependencies_by_component_id(self, component_id) -> List[ComponentDependencyModel]:
        with self.session_context(self.Session()) as session:
            component_dependencies = session.query(ComponentDependency).filter(ComponentDependency.component_id == component_id).all()
            return [ComponentDependencyModel.from_database_model(c) for c in component_dependencies]
        
    def get_component_data_handlings_by_data_name(self, data_name) -> List[ComponentDataHandlingModel]:
        with self.session_context(self.Session()) as session:
            component_data_handlings = session.query(ComponentDataHandling).filter(ComponentDataHandling.data_name == data_name).all()
            return [ComponentDataHandlingModel.from_database_model(c) for c in component_data_handlings]
        
    def get_component_interactions_by_interacts_with(self, interacts_with) -> List[ComponentInteractionModel]:
        with self.session_context(self.Session()) as session:
            component_interactions = session.query(ComponentInteraction).filter(ComponentInteraction.interacts_with == interacts_with).all()
            return [ComponentInteractionModel.from_database_model(c) for c in component_interactions]
        
    def get_component_dependencies_by_depends_on(self, depends_on) -> List[ComponentDependencyModel]:
        with self.session_context(self.Session()) as session:
            component_dependencies = session.query(ComponentDependency).filter(ComponentDependency.depends_on == depends_on).all()
            return [ComponentDependencyModel.from_database_model(c) for c in component_dependencies]
        
    def get_component_data_handlings_by_data_type(self, data_type) -> List[ComponentDataHandlingModel]:
        with self.session_context(self.Session()) as session:
            component_data_handlings = session.query(ComponentDataHandling).filter(ComponentDataHandling.data_type == data_type).all()
            return [ComponentDataHandlingModel.from_database_model(c) for c in component_data_handlings]    
        
    
