from datetime import datetime

def get_system_information(location: str):
        return f"Current Date/Time: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}. Current Time Zone: {datetime.now().astimezone().tzinfo}.  Current Location: {location}"