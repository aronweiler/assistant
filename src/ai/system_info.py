from datetime import datetime
from tzlocal import get_localzone


def get_system_information(location: str):
    

# Get the local time zone in IANA format
    local_timezone = get_localzone()
    return f"User's Current Date/Time: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}.\nUser's Current Time Zone: {local_timezone}.\nUser's Current Location: {location}"
