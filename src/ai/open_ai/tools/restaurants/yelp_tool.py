import requests

def get_yelp_api_key():
    from dotenv import dotenv_values, load_dotenv

    load_dotenv()
    return dotenv_values().get("YELP_API_KEY")

def search_restaurants(api_key, location, term="restaurants", categories="restaurants", open_now=True, price="1,2,3", rating=4.0):
    base_url = "https://api.yelp.com/v3/businesses/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    params = {
        "location": location,
        "term": term,
        "categories": categories,
        "open_now": open_now,
        "price": price,
        "rating": rating,
    }

    try:
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for unsuccessful requests
        data = response.json()
        return data["businesses"]
    except requests.exceptions.RequestException as e:
        print("Error occurred during API request:", e)
        return []

if __name__ == "__main__":    
    yelp_api_key = get_yelp_api_key()

    # Replace "Downtown San Diego" with the location you want to search for restaurants
    location = "Downtown San Diego"

    # Call the function to get a list of restaurants matching the criteria
    restaurants = search_restaurants(api_key=yelp_api_key, location=location, rating=4.0)

    # Display the results
    for idx, restaurant in enumerate(restaurants, 1):
        print(f"{idx}. {restaurant['name']} - Rating: {restaurant['rating']} - Address: {restaurant['location']['address1']}")
