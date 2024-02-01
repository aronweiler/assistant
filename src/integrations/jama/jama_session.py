import requests


class JamaSession:
    def __init__(self, api_url, auth_type="basic", **auth_credentials):
        self.api_url = api_url
        self.auth_type = auth_type
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
        self.session.auth = (username, password)

    def _authenticate_oauth(self, client_id, client_secret):
        # This is a simplified example; actual OAuth flow will require more steps
        token_url = f"{self.api_url}/oauth/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        response = self.session.post(token_url, data=data)
        access_token = response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})

    def make_api_call(self, endpoint, method="GET", data=None):
        url = f"{self.api_url}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        if method == "POST" and data:
            response = self.session.post(url, json=data, headers=headers)
        elif method == "GET":
            response = self.session.get(url, headers=headers)
        else:
            # Add other methods as needed
            pass
        return response.json()
