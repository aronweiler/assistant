

from src.db.models.code import Code


def get_provider_from_url(url:str):
    """
    Returns the source control provider from a URL.

    :param url: The URL to parse.
    :return: The source control provider.
    """
    code_helper = Code()
    
    return code_helper.get_provider_from_url(url)