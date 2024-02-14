import json


class ApplicationConfigurationLoader:
    @staticmethod
    def from_file(file_path):
        with open(file_path, "r") as file:
            config_data = json.load(file)

        return config_data

    @staticmethod
    def save_to_file(config_data, file_path):
        with open(file_path, "w") as file:
            json.dump(config_data, file, indent=4)

