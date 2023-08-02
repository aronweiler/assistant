import requests
from typing import List

# A simple wrapper around the requests library

class RequestsTool:
    def get_request(self, url:str, params:dict[str, str]=None) -> str:
        """A portal to the internet. Use this when you need to get specific content from a website. Input should be a  url (i.e. https://www.google.com). The output will be the text response of the GET request.

        Args:
            url (str): URL to send the request to
            params (dict[str, str]): optional list of tuples or bytes to send in the query string

        Returns:
            str: The text of the response"""
        return requests.get(url, params=params).text

    def post_request(self, url:str, data:dict[str, str]=None) -> str:
        """Use this when you want to POST to a website.
            Input should be a json string with two keys: "url" and "data".
            The value of "url" should be a string, and the value of "data" should be a dictionary of 
            key-value pairs you want to POST to the url.
            Be careful to always use double quotes for strings in the json string
            The output will be the text response of the POST request.
        
        Args:
            url (str): URL to send the request to
            data (dict[str, str]): optional list of tuples, bytes, or file-like object to send in the body of the request
            
            Returns:
                str: The text of the response"""
        
        return requests.post(url, data=data)