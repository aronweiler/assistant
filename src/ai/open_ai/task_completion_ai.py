from ai.abstract_ai import AbstractAI
from ai.open_ai.task_refinement.refine_task import TaskRefiner
from ai.open_ai.task_refinement.step import Step
from ai.ai_result import AIResult

# Implement the TaskCompletionAI class as a subclass of the AbstractAI class.

class TaskCompletionAI(AbstractAI):    

    def configure(self, json_args):
        self.configuration = json_args

        self.task_refiner = TaskRefiner(json_args)
        # openai_with_tools = TaskRefiner(self.config_json["ai"], sys_info)

    def query(self, query: str):

        # First break the request down into pieces if possible
        # This should always use the list tool
        parent_step = self.task_refiner.break_task_into_steps(
            query, Step(query), True
        )

        # Output the steps as a string  
        output_string = parent_step.step
        for step in parent_step.sub_steps:
            # EXECUTE!
            sub_steps = "\t\t".join([s.step for s in step.sub_steps])
            output_string += f"\n\nSTEP: {step.step}\n\tRECOMMENDED TOOL: {step.recommended_tool}\n\tSUB STEPS:\n\t\t {sub_steps}"

        return AIResult(parent_step, output_string)   