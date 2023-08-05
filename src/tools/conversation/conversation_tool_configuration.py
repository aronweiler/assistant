class ConversationToolConfiguration:
    def __init__(self, json_args):
        self.db_env_location = json_args["db_env_location"]
        self.top_k = json_args.get("top_k", 10)
