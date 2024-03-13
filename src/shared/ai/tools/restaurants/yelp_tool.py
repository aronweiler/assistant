from typing import Optional, Union
import requests

from src.shared.ai.tools.tool_registry import register_tool, tool_class


def get_yelp_api_key():
    from dotenv import dotenv_values, load_dotenv

    load_dotenv()
    return dotenv_values().get("YELP_API_KEY")


@register_tool(
    display_name="Search Businesses",
    requires_documents=False,
    description="Searches Yelp for matching criteria and returns a list of businesses.",
    additional_instructions="The location is required. Additionally, you can specify a search term, categories, whether to only return open businesses, price range (1=low-price, 2=med-price, 3=high=price- can be combined), minimum rating, and maximum number of businesses to return.",
    category="Business",
)
def search_businesses(
    location: str,
    number_of_results: int = None,
    search_term: str = None,
    categories: str = None,
    open_now: bool = None,
    price: str = None,
    rating: float = None,
):
    """Searches Yelp for businesses matching the criteria and returns a list of businesses"""

    if not number_of_results:
        number_of_results = 5

    base_url = "https://api.yelp.com/v3/businesses/search"
    headers = {
        "Authorization": f"Bearer {get_yelp_api_key()}",
    }
    params = {
        "location": location,
        "term": search_term,
        "categories": categories,
        "open_now": open_now,
        "price": price,
        "rating": rating,
    }

    try:
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for unsuccessful requests
        data = response.json()
        return get_friendly_results(data["businesses"][:number_of_results])
    except requests.exceptions.RequestException as e:
        print("Error occurred during API request:", e)
        return []


def get_friendly_results(businesses: list):
    # The Yelp API returns a lot of data, but we only want to return a few fields
    # that are relevant to the user
    friendly_results = []
    for business in businesses:
        friendly_results.append(
            {
                "id": business["id"],
                "name": business["name"],
                "is_closed": business["is_closed"],
                "review_count": (
                    business["review_count"] if "review_count" in business else None
                ),
                "rating": business["rating"] if "rating" in business else None,
                "price": business["price"] if "price" in business else None,
                "phone": business["phone"] if "phone" in business else None,
                "address": (
                    business["location"]["display_address"]
                    if "location" in business
                    else None
                ),
                "url": business["url"] if "url" in business else None,
            }
        )

    return friendly_results


def get_business_details(business_id):
    base_url = f"https://api.yelp.com/v3/businesses/{business_id}"
    headers = {
        "Authorization": f"Bearer {get_yelp_api_key()}",
    }

    try:
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()  # Raise an exception for unsuccessful requests
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print("Error occurred during API request:", e)
        return None


@register_tool(
    display_name="Get Business Details",
    help_text="Retrieves details of a specific business.",
    requires_documents=False,
    description="Retrieves details of a specific business, matching the business_id.",
    additional_instructions="business_id is the id of the business, discovered by using the search_businesses tool.",
    category="Business",
)
def get_all_business_details(business_id: str):
    """Retrieves details of all businesses matching the search criteria

    Args:
        business_id (str): The id of the business, discovered by using the search_businesses function

    Returns:
        list: Details of the business
    """

    if business_id:
        business_details = get_business_details(business_id)
        if business_details:
            return business_details

    return f"Could not find details for specified business, {business_id}"


def search_all_business_details(
    location: str,
    search_term: str = "restaurants",
    categories: str = "restaurants",
    open_now: bool = False,
    price: str = "1,2,3",
    rating: float = 3.0,
    limit: int = 10,
):
    """Retrieves details of all businesses matching the search criteria"""
    businesses = search_businesses(
        location, search_term, categories, open_now, price, rating, limit
    )
    if not businesses:
        return []

    all_business_details = []
    for business in businesses:
        business_id = business.get("id")
        if business_id:
            business_details = get_business_details(business_id)
            if business_details:
                all_business_details.append(business_details)

    return get_friendly_results(all_business_details[:limit])


if __name__ == "__main__":
    # Replace "Downtown San Diego" with the location you want to search for restaurants
    location = "Downtown San Diego"

    # Call the function to get a list of restaurants matching the criteria
    restaurants = search_businesses(location=location, rating=4.0)

    # Display the results
    for idx, restaurant in enumerate(restaurants, 1):
        print(
            f"{idx}. {restaurant['name']} - Rating: {restaurant['rating']} - Address: {restaurant['location']['address1']}"
        )
