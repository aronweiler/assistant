import argparse
import logging

from configuration.assistant_configuration import AssistantConfiguration
from utilities.instance_utility import create_instance_from_module_and_class

parser = argparse.ArgumentParser()

# Add arguments
parser.add_argument(
    "--config", type=str, required=True, help="Path to the configuration file"
)
parser.add_argument(
    "--logging_level", type=str, required=False, default="INFO", help="Logging level"
)

# Parse the command-line arguments
args = parser.parse_args()

numeric_level = getattr(logging, args.logging_level.upper(), None)
logging.basicConfig(level=numeric_level)
logging.info("Started logging")

# load the config
config = AssistantConfiguration.from_file(args.config)

# get the ai
if config.ai:
    ai_inst = create_instance_from_module_and_class(
        config.ai.type_configuration.module_name,
        config.ai.type_configuration.class_name,
        config.ai,
    )

else:
    raise ValueError("AI is not defined in the configuration file")

if not config.runners:
    raise ValueError("No runners defined")

# TODO: Make this multi-threaded??
for runner in config.runners:
    if not runner.enabled:
        logging.debug("Skipping disabled runner, " + runner["runner"]["type"])
        continue

    # If there are arguments in the runner config, pass them on
    if runner.arguments and runner.arguments != {}:
        runner_instance = create_instance_from_module_and_class(
            runner.type_configuration.module_name,
            runner.type_configuration.class_name,
            runner.arguments,
        )

    else:
        runner_instance = create_instance_from_module_and_class(
            runner.type_configuration.module_name, runner.type_configuration.class_name
        )

    # TODO: This is a hack, but it works for now
    # This is here because starting FastAPI in proc demands it (see the RestAPIRunner)
    if callable(runner):
        runner_instance(ai_inst)

    runner_instance.run(abstract_ai=ai_inst)
