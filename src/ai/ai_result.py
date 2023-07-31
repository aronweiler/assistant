class AIResult:

    def __init__(self, raw_result, result_string, source_documents = None) -> None:
        self.raw_result = raw_result
        self.result_string = result_string        
        self.source_documents = source_documents