import tiktoken

def get_token_count(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string.  cl100k_base is used for text-embedding-ada-002"""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens
