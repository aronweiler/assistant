from datetime import datetime
from tzlocal import get_localzone


def get_system_information(location: str) -> str:
    """
    Get the system information including the current date/time, time zone, and location.

    :param location: The location of the user as a string.
    :return: A formatted string containing the date/time, time zone, and location.
    """
    # Get the local time zone in IANA format
    local_timezone = get_localzone()
    current_datetime = datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    
    # Format the system information string
    system_info = (
        f"User's Current Date/Time: {current_datetime}.
"
        f"User's Current Time Zone: {local_timezone}.
"
        f"User's Current Location: {location}"
    )
    return system_info
