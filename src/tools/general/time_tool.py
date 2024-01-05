import pytz
from datetime import datetime

from src.ai.tools.tool_registry import register_tool


class TimeTool:
    @register_tool(
        description="Get the current time in the specified IANA time zone.",
        additional_instructions="current_time_zone (str): The IANA time zone to get the current time in, for example: 'America/New_York'.",
    )
    def get_time(self, current_time_zone: str) -> str:
        """Get the current time in the specified IANA time zone

        Args:
            current_time_zone (str): The IANA time zone to get the current time in

            Returns:
                str: The current time in the specified time zone"""
        try:
            time_zone = pytz.timezone(current_time_zone)

            # Get the current datetime in the specified time zone
            current_datetime = datetime.now(time_zone)

            return current_datetime.strftime("%A, %B %d, %Y %I:%M %p")
        except:
            return "Invalid time zone specified.  Make sure you use IANA time zone names.  Such as 'America/New_York'"
