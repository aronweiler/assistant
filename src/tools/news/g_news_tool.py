from gnews import GNews

class GNewsTool:
    def __init__(self, max_results:int=5):
        self.google_news = GNews(max_results=max_results)

    def get_news(self, query:str):
        """Get a list of news headlines for the specified query. 

        Args:
            query (str): Keyword description of the news you want to look for        
        """
        
        headlines = self.google_news.get_news(key=query)
    
        headlines = self.parse_news(headlines)

        return headlines

    def get_top_news(self):
        """Get a list of the top news story headlines"""
        
        headlines = self.google_news.get_top_news()
    
        headlines = self.parse_news(headlines)

        return headlines

    def get_full_article(self, url:str):
        """Get the full article for the specified URL.  Use this if a user more details on a specific story or headline.  Note: This can only be used if you have the full article URL.

        Args:
            url (str): The URL of the article you want to get the full text for
        """
        
        full_article = self.google_news.get_full_article(url=url)

        return full_article

    def get_news_by_location(self, location:str):
        """Get a list of the headlines for the specified location.

        Args:
            location (str): Location to get the news for.  Should be a city, state, or country only.  e.g. "New York", "United States", "California", etc.
        """
        
        location = location.replace(" ", "+")

        headlines =  self.google_news.get_news_by_location(location=location)

        headlines = self.parse_news(headlines)

        return headlines

    def parse_news(self, news:list):
        """Parse the news list into a more readable format.

        Args:
            news (list): List of news headlines

        Returns:
            list: List of news headlines in a more readable format
        """
        
        parsed_news = []

        for headline in news:
            parsed_news.append(f"{headline['description']}\n{headline['url']}\n{headline['published date']}")

        return parsed_news