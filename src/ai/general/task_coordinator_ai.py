from ai.abstract_ai import AbstractAI
from ai.ai_result import AIResult
from utilities.instance_tools import create_instance_from_module_and_class

class TaskCoordinatorAI(AbstractAI):
    def configure(self, json_args):
        self.configuration = json_args

        self.subordinate_ais = []

        # Load the subordinate AIs
        for ai_config in json_args["subordinate_ais"]:
            ai = self.load_subordinate_ai(ai_config)
            self.subordinate_ais.append(ai)

        # Ensure that the proper subordinate AIs are loaded
        self.task_refinement_ai = json_args["task_refinement_ai"]
        self.tool_using_ai = json_args["tool_using_ai"]        

    def query(self, query: str):
        # Get the refinement
        refinement = self.get_subordinate_ai(self.task_refinement_ai).query(query)

        # Run the refined steps through the tool-using AI
        results = []
        tool_using_ai = self.get_subordinate_ai(self.tool_using_ai)
        for step in refinement.raw_result.sub_steps:
            results.append(tool_using_ai.query(step.step))

        # TODO: Combine results and return something nice for the user

        return AIResult(results, "Complete!")

    def get_subordinate_ai(self, ai_name):
        for ai in self.subordinate_ais:
            if ai.configuration.name == ai_name:
                return ai
            
        raise Exception(f"Could not find subordinate AI with name {ai_name}")

    def load_subordinate_ai(self, ai_config):
        instance = create_instance_from_module_and_class(ai_config["module"], ai_config["class_name"])
        instance.configure(json_args=ai_config["arguments"])
        return instance
    
        

        