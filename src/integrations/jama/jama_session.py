from base64 import b64encode
from json import JSONDecodeError
from requests.auth import HTTPBasicAuth
import logging
import requests


class JamaSession:
    def __init__(
        self, api_url, api_version="v1", auth_type="basic", **auth_credentials
    ):
        self.api_url = api_url
        self.auth_type = auth_type
        self.api_version = api_version

        self.session = requests.Session()

        if auth_type == "basic":
            self._authenticate_basic(
                auth_credentials.get("username"), auth_credentials.get("password")
            )
        elif auth_type == "oauth":
            self._authenticate_oauth(
                auth_credentials.get("client_id"), auth_credentials.get("client_secret")
            )

    def _authenticate_basic(self, username, password):
        basic = HTTPBasicAuth(username=username, password=password)

        self.session.auth = basic

    def _authenticate_oauth(self, client_id, client_secret):
        # This is a simplified example; actual OAuth flow will require more steps
        token_url = f"{self.api_url}/oauth/token"
        data = {"grant_type": "client_credentials"}

        response = self.session.post(
            token_url,
            data=data,
            auth=HTTPBasicAuth(username=client_id, password=client_secret),
        )
        access_token = response.json().get("access_token")

        if not access_token:
            logging.error("Could not authenticate with Jama")

        self.session.headers.update({"Authorization": f"Bearer {access_token}"})

    def make_api_call(self, endpoint, method="GET", data=None):
        url = f"{self.api_url}/{self.api_version}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        if method == "POST" and data:
            response = self.session.post(url, json=data, headers=headers)
        elif method == "GET":
            response = self.session.get(url, headers=headers)
        else:
            # Add other methods as needed
            pass
        
        try:
            return response.json()
        except JSONDecodeError:
            return response.text


if __name__ == "__main__":
    jama = JamaSession(
        api_url="xxxx", auth_type="oauth", client_id="xxxx", client_secret="xxxxx"
    )

    print(jama.make_api_call("users/current", method="GET"))
    print(jama.make_api_call("projects", method="GET"))
