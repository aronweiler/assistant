import importlib
import logging

def create_instance_from_module_and_class(
    module_name: str, class_name: str, constructor_args=None
):
    try:
        module = importlib.import_module(module_name)

        # dynamically instantiate the tool based on the parameters
        if constructor_args is not None:
            instance = getattr(module, class_name)(constructor_args)
        else:
            instance = getattr(module, class_name)()

        return instance
    except Exception as e:
        logging.error("Error creating tool: " + str(e))
        return None