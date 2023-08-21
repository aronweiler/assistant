import python_weather
import json
import asyncio
import os
from datetime import datetime
import logging


class WeatherTool:

    def get_weather(self, location: str, date: str = None) -> str:
        """Get the weather for a location and date.
        Location is required, and should be a string representing the City, State, and Country (if outside the US) of the location to get the weather for, e.g. "Phoenix, AZ".
        Date is optional, and should be a string ("%Y-%m-%d") representing the date to get the weather for, e.g. "2023-4-15".  If no date is provided, the weather for the current date will be returned."""
        
        logging.debug(f"Weather Query: {location}, {date}")
        
        try:
           
            # Parse the date string from the query
            date_format = "%Y-%m-%d"
            try:
                if date is not None:
                    parsed_date = datetime.strptime(date, date_format).date() 
                else:
                    parsed_date = datetime.now().date()
            except:
                parsed_date = None

            try:   
                
                result = self.get_or_create_eventloop().run_until_complete(self.get(location))         
            except asyncio.TimeoutError:
                return "Timeout: The operation took too long to complete."

            if parsed_date is None or parsed_date == datetime.now().date():
                logging.debug("Looking for the current weather")
                return f"Temperature: {result.current.temperature} degrees. Feels like: {result.current.feels_like} degrees. Description: {result.current.description}. Humidity: {result.current.humidity}."
            else:
                logging.debug("Looking for a forecast for the date: " + str(parsed_date))
                # Look for the date in the forecast
                for forecast in result.forecasts:
                    logging.debug("Forecast date: " + str(forecast.date))
                    if forecast.date == parsed_date:
                        return f"Summarize in one sentence the following hourly forecast for {forecast.date}:\n" + "\n".join([f"Time: {fc.time}, temp: {fc.temperature}, description: {fc.description}" for fc in forecast.hourly])
                        #return f"Low temp: {forecast.lowest_temperature} degrees. High temp: {forecast.highest_temperature} degrees."
                
                return f"Could not find a forecast for {parsed_date}."
        except Exception as e:
            logging.error(e)
            return "An error occurred while processing your request."

    async def get(self, query):
        weather_client = python_weather.Client(unit=python_weather.IMPERIAL)

        # Get the current weather of the city
        weather = await weather_client.get(query)

        # Return the weather
        return weather

    def get_or_create_eventloop(self) -> asyncio.AbstractEventLoop:
        try:
            return asyncio.get_event_loop()
        except RuntimeError as ex:
            if "There is no current event loop in thread" in str(ex):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                return asyncio.get_event_loop()
            else:
                raise ex
            


# Test code
if __name__ == "__main__":
    tool = WeatherTool()

    result = tool.run("{\"location\": \"San Diego\", \"date\": \"2023-07-29\"}")

    print(result)