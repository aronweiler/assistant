import importlib
import logging

def create_instance_from_module_and_class(
    module_name: str, class_name: str, constructor_kwargs=None
):
    try:
        module = importlib.import_module(module_name)

        # dynamically instantiate the tool based on the parameters
        if constructor_kwargs is not None:
            instance = getattr(module, class_name)(**constructor_kwargs)
        else:
            instance = getattr(module, class_name)()

        return instance
    except Exception as e:
        logging.error(f"Error creating an instance of {class_name} class: {str(e)}")
        return None