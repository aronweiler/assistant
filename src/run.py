import argparse
import json
import logging

from ai.open_ai.task_refinement_ai import TaskRefinementAI
from runners.console.console_runner import ConsoleRunner
from runners.voice.voice_runner import VoiceRunner

AI_TYPES = {
    "task_refinement_ai": TaskRefinementAI,
}

RUNNER_TYPES = {
    "console": ConsoleRunner,
    "voice": VoiceRunner
}

parser = argparse.ArgumentParser()

# Add arguments
parser.add_argument("--config", type=str, required=True, help="Path to the configuration file")
parser.add_argument("--logging_level", type=str, required=False, default="INFO", help="Logging level")

# Parse the command-line arguments
args = parser.parse_args()

numeric_level = getattr(logging, args.logging_level.upper(), None)
logging.basicConfig(level=numeric_level)
logging.info('Started logging')

# load the config
with open(args.config) as config_file:
    config = json.load(config_file)

ai_type = config["ai"]["type"]
ai_args = config["ai"]["arguments"]

logging.debug("ai_type: " + ai_type)

# Print out the list of arguments in a nice human readable format:
logging.debug("ai_args:")
for key, value in ai_args.items():
    logging.debug(f"{key}: {value}")


# get the ai
ai_class = AI_TYPES.get(ai_type)
if ai_class:
    ai = ai_class()
    try:
        ai.configure(ai_args)
    except Exception as e:
        logging.debug("Error configuring AI: " + str(e))
        raise e
else:
    raise ValueError(f"ai_type is undefined, {ai_type}")

# If the runners node exists, get that.  Otherwise get the runner node, and put it into a list.  If the runner node doesn't exist, throw an error.
if "runners" in config:
    runners = config["runners"]
else:
    runners = [config]

if not runners:
    raise ValueError("No runners defined")

# TODO: Make this multi-threaded??
for runner in runners:
    runner_enabled = runner["runner"].get("enabled", True)

    if not runner_enabled:
        logging.debug("Skipping disabled runner, " + runner["runner"]["type"])
        continue

    runner_type = runner["runner"]["type"]
    runner_args = runner["runner"]["arguments"]
    logging.debug("runner_type: " + runner_type)

    # Print out the list of arguments in a nice human readable format:
    logging.debug("runner_args:")
    for key, value in runner_args.items():
        logging.debug(f"{key}: {value}")

    runner_class = RUNNER_TYPES.get(runner_type)
    if runner_class:
        # If there are arguments in the runner config, pass them on
        if runner_args:
            runner = runner_class(runner_args)
        else:
            runner = runner_class()

        # Configure the runner
        # Reserved for later
        runner.configure()

        if callable(runner):
            runner(
                ai
            )  # This is here because starting FastAPI in proc demands it (see the RestAPIRunner)
        runner.run(abstract_ai=ai)
    else:
        raise ValueError(f"runner type is undefined, {runner_type}")
