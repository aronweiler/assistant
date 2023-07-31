import requests

class YelpTool:

    def get_yelp_api_key(self):
        from dotenv import dotenv_values, load_dotenv

        load_dotenv()
        return dotenv_values().get("YELP_API_KEY")

    def search_businesses(self, location:str, search_term:str="restaurants", categories:str="restaurants", open_now:bool=False, price:str="1,2,3", rating:float=3.0, limit:int=10):
        """Searches Yelp for businesses matching the criteria and returns a list of businesses

        Args:
            location (str): The location to search for businesses
            search_term (str, optional): The term to search for. Defaults to "restaurants".
            categories (str, optional): The categories to search for. Defaults to "restaurants".
            open_now (bool, optional): Whether to only return businesses open now. Defaults to False.
            price (str, optional): The price range to search for. Defaults to "1,2,3" (1=low-price, 2=med-price, 3=high=price).
            rating (float, optional): The minimum rating to search for. Defaults to 3.0.
            limit (int, optional): The maximum number of businesses to return. Defaults to 10.

        Returns:
            list: A list of businesses matching the search criteria
            """

        base_url = "https://api.yelp.com/v3/businesses/search"
        headers = {
            "Authorization": f"Bearer {self.get_yelp_api_key()}",
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
            return self.get_friendly_results(data["businesses"][:limit])
        except requests.exceptions.RequestException as e:
            print("Error occurred during API request:", e)
            return []

    def get_friendly_results(self, businesses:list):
        # The Yelp API returns a lot of data, but we only want to return a few fields
        # that are relevant to the user
        friendly_results = []
        for business in businesses:
            friendly_results.append({
                "id": business["id"],
                "name": business["name"],
                "is_closed": business["is_closed"],
                "review_count": business["review_count"],                
                "rating": business["rating"],
                "price": business["price"],
                "phone": business["phone"],
                "address": business["location"]["display_address"],
                "url": business["url"],
            })            

        return friendly_results


    def get_business_details(self, business_id):
        base_url = f"https://api.yelp.com/v3/businesses/{business_id}"
        headers = {
            "Authorization": f"Bearer {self.get_yelp_api_key()}",
        }

        try:
            response = requests.get(base_url, headers=headers)
            response.raise_for_status()  # Raise an exception for unsuccessful requests
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print("Error occurred during API request:", e)
            return None

    def get_all_business_details(self, business_id:str):
        """Retrieves details of all businesses matching the search criteria

        Args:
            business_id (str): The id of the business, discovered by using the search_businesses function

        Returns:
            list: Details of the business
        """
        
        if business_id:
            business_details = self.get_business_details(business_id)
            if business_details:
                return business_details

        return f"Could not find details for specified business, {business_id}"

    def search_all_business_details(self, location:str, search_term:str="restaurants", categories:str="restaurants", open_now:bool=False, price:str="1,2,3", rating:float=3.0, limit:int=10):
        """Retrieves details of all businesses matching the search criteria

        Args:
            location (str): The location to search for businesses
            search_term (str, optional): The term to search for. Defaults to "restaurants".
            categories (str, optional): The categories to search for. Defaults to "restaurants".
            open_now (bool, optional): Whether to only return businesses open now. Defaults to False.
            price (str, optional): The price range to search for. Defaults to "1,2,3" (1=low-price, 2=med-price, 3=high=price).
            rating (float, optional): The minimum rating to search for. Defaults to 3.0.
            limit (int, optional): The maximum number of businesses to return. Defaults to 10.

        Returns:
            list: A list of businesses matching the search criteria, and all details for each business
        """
        businesses = self.search_businesses(location, search_term, categories, open_now, price, rating, limit)
        if not businesses:
            return []

        all_business_details = []
        for business in businesses:
            business_id = business.get("id")
            if business_id:
                business_details = self.get_business_details(business_id)
                if business_details:
                    all_business_details.append(business_details)

        return self.get_friendly_results(all_business_details[:limit])
        

if __name__ == "__main__":    
    # Create an instance of the tool
    yelp_tool = YelpTool()

    # Replace "Downtown San Diego" with the location you want to search for restaurants
    location = "Downtown San Diego"

    # Call the function to get a list of restaurants matching the criteria
    restaurants = yelp_tool.search_restaurants(location=location, rating=4.0)

    # Display the results
    for idx, restaurant in enumerate(restaurants, 1):
        print(f"{idx}. {restaurant['name']} - Rating: {restaurant['rating']} - Address: {restaurant['location']['address1']}")
