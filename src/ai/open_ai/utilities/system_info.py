import datetime


class SystemInfo:
    def __init__(self, user_email = "Not Set", user_location = "Not Set", user_name = "Not Set"):
        self.name = "System Info"
        self.user_email = user_email
        self.user_location = user_location
        self.user_name = user_name

    def get(self):
        system_info_string = f"System Info: Current Date/Time: {datetime.datetime.now()}, User Email: {self.user_email}, User Location: {self.user_location}, User Name: {self.user_name}"

        return system_info_string
