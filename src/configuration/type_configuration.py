class TypeConfiguration:
    def __init__(self, module_name, class_name) -> None:
        self.module_name = module_name
        self.class_name = class_name
        pass

    @staticmethod
    def from_dict(config: dict):
        module_name = config["module_name"]
        class_name = config["class_name"]

        return TypeConfiguration(module_name, class_name)
