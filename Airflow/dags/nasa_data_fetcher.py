import uuid
import json
import requests
import os
import logging
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from kafka import KafkaProducer
import time

# Define default arguments for the DAG
default_args = {
    'owner': 'airscholar',
    'start_date': datetime(2024, 10, 2, 10, 00),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Function to fetch NASA NEO data
def get_nasa_data(**kwargs) -> dict:
    api_key = os.getenv("NASA_API_KEY")  # Load from environment variable
    if not api_key:
        logging.error("NASA API key is not set in environment variables.")
        return {}

    # Use execution_date from Airflow to get the current date for this run
    execution_date = kwargs['execution_date']
    
    # Last 7 days 
    end_date = execution_date.strftime("%Y-%m-%d")
    start_date = (execution_date - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Construct the URL with the dynamic date range
    url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={start_date}&end_date={end_date}&api_key={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from NASA API: {e}")
        return {}

# Function to format NASA NEO data
def format_nasa_data(data) -> list:
    formatted_data = []
    for date, asteroids in data.get('near_earth_objects', {}).items():
        for asteroid in asteroids:
            important_data = {
                "id": str(uuid.uuid4()),  # Consider hashing the asteroid ID for consistency
                "Date": date,
                "Name": asteroid["name"],
                "Estimated Diameter (km)": {
                    "min": asteroid["estimated_diameter"]["kilometers"]["estimated_diameter_min"],
                    "max": asteroid["estimated_diameter"]["kilometers"]["estimated_diameter_max"]
                },
                "Is Potentially Hazardous": asteroid["is_potentially_hazardous_asteroid"],
                "Close Approach Date": asteroid["close_approach_data"][0]["close_approach_date"],
                "Relative Velocity (km/s)": asteroid["close_approach_data"][0]["relative_velocity"]["kilometers_per_second"],
                "Miss Distance (km)": asteroid["close_approach_data"][0]["miss_distance"]["kilometers"]
            }
            formatted_data.append(important_data)
    return formatted_data

# Function to retrieve and format data
def retrieve_and_format_data(**kwargs) -> list:
    data = get_nasa_data(**kwargs)
    return format_nasa_data(data)

# Function to stream data to Kafka
def stream_data(**kwargs):
    producer = KafkaProducer(bootstrap_servers=os.getenv("KAFKA_BROKER"),
                             value_serializer=lambda v: json.dumps(v).encode('utf-8'))
    
    try:
        logging.info('Retrieving and formatting NASA NEO data...')
        formatted_data = retrieve_and_format_data(**kwargs)

        if formatted_data:
            for item in formatted_data:
                producer.send(os.getenv("KAFKA_TOPIC"), value=item)
                time.sleep(0.1)  # Optional: throttle the requests, adjust as needed

    except Exception as e:
        logging.error(f'An error occurred while streaming data: {e}')
    finally:
        producer.flush()  # Ensure all messages are sent
        producer.close()  

# Define the DAG
with DAG('nasa_neo_user_automation',
         default_args=default_args,
         schedule_interval='@daily',
         catchup=False) as dag:

    streaming_task = PythonOperator(
        task_id='stream_nasa_data_to_kafka',
        python_callable=stream_data,
        provide_context=True 
    )
