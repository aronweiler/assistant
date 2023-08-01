from ai.abstract_ai import AbstractAI
from ai.ai_result import AIResult
from ai.open_ai.configuration import OpenAIConfiguration
from utilities.instance_tools import create_instance_from_module_and_class


class TaskCoordinatorAI(AbstractAI):
    def configure(self, json_args):
        self.configuration = OpenAIConfiguration(json_args)

        self.subordinate_ais = []

        # Load the subordinate AIs
        for ai_config in json_args["subordinate_ais"]:
            ai = self.load_subordinate_ai(ai_config)
            self.subordinate_ais.append(ai)

        # Ensure that the proper subordinate AIs are loaded
        self.task_refinement_ai: AbstractAI = json_args["task_refinement_ai"]
        self.tool_using_ai: AbstractAI = json_args["tool_using_ai"]
        self.collapse_results_ai: AbstractAI = json_args["collapse_results_ai"]

    def query(self, query: str):
        # Get the refinement
        refiner = self.get_subordinate_ai(self.task_refinement_ai)
        refinement_result = refiner.query(query)

        # Run the refined steps through the tool-using AI
        raw_step_results = []
        result_strings = []
        tool_using_ai = self.get_subordinate_ai(self.tool_using_ai)
        for step in refinement_result.raw_result.sub_steps:
            tool_use_result = tool_using_ai.query(step.step)
            # Do I need to unwrap these results?
            raw_step_results.append(tool_use_result.raw_result)
            result_strings.append(tool_use_result.result_string)

        # Collapse the results
        collapse_results_ai = self.get_subordinate_ai(self.collapse_results_ai)
        results = collapse_results_ai.query(result_strings, query)

        return AIResult(
            {
                "initial_query": query,
                "refinement_result": refinement_result,
                "raw_step_results": raw_step_results,
            },
            results.result_string,
        )

    def get_subordinate_ai(self, ai_name) -> AbstractAI:
        for ai in self.subordinate_ais:
            if isinstance(ai.configuration, OpenAIConfiguration):
                name_value = ai.configuration.name
            elif isinstance(ai.configuration, dict):
                name_value = ai.configuration["name"]

            if name_value == ai_name:
                return ai

        raise Exception(f"Could not find subordinate AI with name {ai_name}")

    def load_subordinate_ai(self, ai_config):
        instance = create_instance_from_module_and_class(
            ai_config["module"], ai_config["class_name"]
        )
        instance.configure(json_args=ai_config["arguments"])
        return instance
