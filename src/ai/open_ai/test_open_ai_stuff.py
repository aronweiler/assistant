import logging
import json
import sys

# For testing
# Add the root path to the python path so we can import the database
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from ai.open_ai.system_info import SystemInfo
from ai.open_ai.task_refinement.refine_task import TaskRefiner
from ai.open_ai.step import Step


def test_task_refiner(sys_info, config_json):
    openai_with_tools = TaskRefiner(config_json["ai"], sys_info)

    user_input = "Make a reservation at a 4 star restaurant in downtown San Diego tomorrow night for me and Susan Workman.  I would like to sit outside.  Make sure the restaurant serves steak, and that you send a calendar invite to Susan."

    # First break the request down into pieces if possible
    # This should always use the list tool
    parent_step = openai_with_tools.break_task_into_steps(
        user_input, Step(user_input), True
    )

    for step in parent_step.sub_steps:
        # EXECUTE!
        sub_steps = "\t\t".join([s.step for s in step.sub_steps])
        print(
            f"STEP: {step.step}\n\tRECOMMENDED TOOL: {step.recommended_tool}\n\tSUB STEPS:\n\t\t {sub_steps}"
        )

        # - Evaluate the conversation for the next step
        # - If there's an evaluation, and it's not done, execute the next step
        # - If the execution result is a function call, then we need to call the function
        # - If the execution result is not a function call, then we need to evaluate for the next step
        # - If the evaluation is done, then we are done


# Testing - doesn't work anymore
if __name__ == "__main__":
    # set logging to DEBUG
    logging.basicConfig(level=logging.DEBUG)

    # Create some system info
    sys_info = SystemInfo("aronweiler@gmail.com", "San Diego, CA", "Aron Weiler")

    with open("src\\ai\\open_ai\\sample.json") as config_file:
        config_json = json.load(config_file)

    # Test the refinement of tasks into units that can be independently executed
    test_task_refiner(sys_info, config_json)
