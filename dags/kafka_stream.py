import requests
import json
import uuid

def get_data(api_key, start_date, end_date):
    """
    Fetch data from NASA's NEO API for the given date range.

    Args:
        api_key (str): The API key for authentication.
        start_date (str): The start date for data retrieval (YYYY-MM-DD).
        end_date (str): The end date for data retrieval (YYYY-MM-DD).

    Returns:
        list: A list of near-Earth objects if successful, None otherwise.
    """
    # Set up the API URL
    url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={start_date}&end_date={end_date}&api_key={api_key}"

    # Fetch data from the NEO API
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        return data['near_earth_objects']
    else:
        print(f"Error fetching data: {response.status_code}")
        return None

def format_data(asteroids):
    """
    Format asteroid data into a structured format.

    Args:
        asteroids (list): A list of asteroid data.

    Returns:
        list: A list of formatted asteroid data.
    """
    formatted_data = []

    for asteroid in asteroids:
        # Extract the first close approach data if available
        location = asteroid["close_approach_data"][0] if asteroid["close_approach_data"] else {}

        # Create a structured dictionary for the asteroid
        data = {
            'id': str(uuid.uuid4()),  # Generate a unique ID for each asteroid
            'name': asteroid["name"],
            'is_potentially_hazardous': asteroid["is_potentially_hazardous_asteroid"],
            'estimated_diameter': {
                'min_meters': asteroid["estimated_diameter"]["meters"]["estimated_diameter_min"],
                'max_meters': asteroid["estimated_diameter"]["meters"]["estimated_diameter_max"]
            },
            'close_approach_date': location.get("close_approach_date", "N/A"),
            'miss_distance_km': location.get("miss_distance", {}).get("kilometers", "N/A"),
            'relative_velocity_kmh': location.get("relative_velocity", {}).get("kilometers_per_hour", "N/A")
        }

        formatted_data.append(data)

    return formatted_data

def stream_data(formatted_data):
    """
    Print formatted asteroid data in JSON format.

    Args:
        formatted_data (list): A list of formatted asteroid data.
    """
    for asteroid in formatted_data:
        print(json.dumps(asteroid, indent=4))

def main(api_key, start_date, end_date):
    """
    Main execution function to fetch, format, and print asteroid data.

    Args:
        api_key (str): The API key for authentication.
        start_date (str): The start date for data retrieval (YYYY-MM-DD).
        end_date (str): The end date for data retrieval (YYYY-MM-DD).
    """
    asteroids_data = get_data(api_key, start_date, end_date)

    if asteroids_data:
        for date, asteroids in asteroids_data.items():
            print(f"\nDate: {date}")
            formatted_data = format_data(asteroids)
            stream_data(formatted_data)

# Main execution parameters
if __name__ == "__main__":
    API_KEY = "wSJjaC224VWXNgCnlzpWSpODlYNyfdeNzUMRRjBU"  # Replace with your actual API key
    START_DATE = "2024-09-21"
    END_DATE = "2024-09-21"

    main(API_KEY, START_DATE, END_DATE)
