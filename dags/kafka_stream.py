from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
import json
import uuid

def get_data(api_key, start_date, end_date, **kwargs):
    """
    Fetch data from NASA's NEO API for the given date range.

    Args:
        api_key (str): The API key for authentication.
        start_date (str): The start date for data retrieval (YYYY-MM-DD).
        end_date (str): The end date for data retrieval (YYYY-MM-DD).

    Returns:
        list: A list of near-Earth objects if successful, raises an error otherwise.
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
        raise ValueError(f"Error fetching data: {response.status_code}")


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
            formatted_data = format_data(asteroids)
            stream_data(formatted_data)


# Define the default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 9, 21),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


# Define the DAG
with DAG('nasa_neo_data_fetcher',
         default_args=default_args,
         schedule_interval='@daily',  # Adjust as needed
         catchup=False) as dag:

    fetch_data = PythonOperator(
        task_id='fetch_nasa_data',
        python_callable=main,
        op_kwargs={
            'api_key': "wSJjaC224VWXNgCnlzpWSpODlYNyfdeNzUMRRjBU",  # Use environment variable in production
            'start_date': "2024-09-21",
            'end_date': "2024-09-21"
        }
    )

    fetch_data
