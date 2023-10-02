from datetime import datetime


def get_system_information(location: str):
    return f"User's Current Date/Time: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}.\nUser's Current Time Zone: {datetime.now().astimezone().tzinfo}.\nUser's Current Location: {location}"
