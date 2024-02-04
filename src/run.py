import argparse
import logging

from src.configuration.assistant_configuration import (
    AssistantConfiguration,
    AssistantConfigurationLoader,
)
from src.configuration.runner_configuration import RunnerConfig
from src.utilities.instance_utility import create_instance_from_module_and_class

from src.ai.general_ai import GeneralAI
from src.ai.voice.runner import Runner

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # Add arguments
    parser.add_argument(
        "--config", type=str, required=True, help="Path to the configuration file"
    )
    parser.add_argument(
        "--logging_level",
        type=str,
        required=False,
        default="INFO",
        help="Logging level",
    )

    # Parse the command-line arguments
    args = parser.parse_args()

    numeric_level = getattr(logging, args.logging_level.upper(), None)
    logging.basicConfig(level=numeric_level)
    logging.info("Started logging")

    runner_config: RunnerConfig = RunnerConfig.load_from_file(args.config)
    assistant_config: AssistantConfiguration = AssistantConfigurationLoader.from_file(
        args.config
    )

    # Create the AI instance
    ai_inst = GeneralAI(assistant_config, runner_config.arguments.conversation_id)

    # If there are arguments in the runner config, pass them on
    if runner_config.arguments:
        runner_instance: Runner = create_instance_from_module_and_class(
            runner_config.module_name,
            runner_config.class_name,
            vars(runner_config.arguments),
        )

    else:
        runner_instance: Runner = create_instance_from_module_and_class(
            runner_config.module_name,
            runner_config.class_name,
        )

    # TODO: This is a hack, but it works for now
    # This is here because starting FastAPI in proc demands it (see the RestAPIRunner)
    if callable(runner_instance):
        runner_instance(ai_inst)

    runner_instance.run(abstract_ai=ai_inst)
