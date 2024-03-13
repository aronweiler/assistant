from gnews import GNews

from src.shared.ai.tools.tool_registry import register_tool


@register_tool(
    display_name="Get News for Topic",
    help_text="Get a list of news headlines and article URLs for a specified term.",
    requires_documents=False,
    description="Get a list of news headlines and article URLs for a specified term.",
    additional_instructions="When using this tool, always return the Headline, whatever summary there is, the source, and the URL.",
    category="News",
)
def get_news_for_topic(query: str, max_results: int = 5):
    """Use this to get a list of news headlines and article URLs for a specified term.

    Args:
        query (str): Keyword description of the news you want to look for.  Query should not be empty!
    """
    google_news = GNews(max_results=max_results)
    headlines = google_news.get_news(key=query)

    headlines = parse_news(headlines)

    return "----".join(headlines)


@register_tool(
    display_name="Get Top News Headlines",
    help_text="Get a list of the top news story headlines and article URLs.",
    requires_documents=False,
    description="Get a list of headlines and article URLs for the top news headlines.",
    additional_instructions="When using this tool, always return the headline, the summary, the source, and the URL to the user.",
    category="News",
)
def get_top_news_headlines(max_results: int = 5):
    """Use this to get a list of the top news story headlines and article URLs"""

    google_news = GNews(max_results=max_results)
    headlines = google_news.get_top_news()

    headlines = parse_news(headlines)

    return "----".join(headlines)


@register_tool(
    display_name="Get Full Article",
    help_text="Use this to get the full article for the specified headline URL.  Note: This can only be used if you already have the article URL, which means that the other news tools need to be enabled.",
    requires_documents=False,
    description="Use this to get the full article for the specified headline URL.  Note: This can only be used if you already have the article URL.",
    additional_instructions="url (str): The URL of the article you want to get the full text for, previously returned by get_top_news_headlines or get_news_by_location.",
    category="News",
)
def get_full_article(url: str, max_results: int = 5):
    """Use this to get the full article for the specified headline URL.  Note: This can only be used if you already have the article URL.

    Args:
        url (str): The URL of the article you want to get the full text for
    """
    google_news = GNews(max_results=max_results)
    full_article = google_news.get_full_article(url=url)

    return full_article


@register_tool(
    display_name="Get News by Location",
    help_text="Get a list of the headlines and article URLs for the specified location.",
    requires_documents=False,
    description="Get a list of the headlines and article URLs for the specified location.",
    additional_instructions="location (str): Location to get the news for.  Should be a city, state, or country only.  e.g. 'New York', 'United States', 'California', etc.",
    category="News",
)
def get_news_by_location(location: str, max_results: int = 5):
    """Get a list of the headlines and article URLs for the specified location.

    Args:
        location (str): Location to get the news for.  Should be a city, state, or country only.  e.g. "New York", "United States", "California", etc.
    """

    location = location.replace(" ", "+")

    google_news = GNews(max_results=max_results)
    headlines = google_news.get_news_by_location(location=location)

    headlines = parse_news(headlines)

    return "----".join(headlines)


def parse_news(news: list):
    """Parse the news list into a more readable format.

    Args:
        news (list): List of news headlines

    Returns:
        list: List of news headlines in a more readable format
    """

    parsed_news = []

    for headline in news:
        parsed_news.append(
            f"{headline['description']}\n{headline['url']}\n{headline['published date']}"
        )

    return parsed_news
