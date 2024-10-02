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
    'start_date': datetime(2023, 9, 3, 10, 00),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Function to fetch NASA NEO data
def get_nasa_data():
    api_key = os.getenv("NASA_API_KEY")  # Load from environment variable
    start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={start_date}&end_date={start_date}&api_key={api_key}"

    response = requests.get(url)
    response.raise_for_status()
    return response.json()

# Function to format NASA NEO data
def format_nasa_data(data):
    formatted_data = []
    for date, asteroids in data['near_earth_objects'].items():
        for asteroid in asteroids:
            important_data = {
                "id": str(uuid.uuid4()),
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

# Function to stream data to Kafka
def stream_data():
    producer = KafkaProducer(bootstrap_servers=os.getenv("KAFKA_BROKER"), 
                             value_serializer=lambda v: json.dumps(v).encode('utf-8'))

    try:
        data = get_nasa_data()
        formatted_data = format_nasa_data(data)

        for item in formatted_data:
            producer.send(os.getenv("KAFKA_TOPIC"), value=item)
            time.sleep(1)  # Optional: throttle the requests

    except Exception as e:
        logging.error(f'An error occurred: {e}')
    finally:
        producer.flush()  # Ensure all messages are sent
        producer.close()  # Close the producer

# Define the DAG
with DAG('nasa_neo_user_automation',
         default_args=default_args,
         schedule_interval='@daily',
         catchup=False) as dag:

    streaming_task = PythonOperator(
        task_id='stream_nasa_data_to_kafka',
        python_callable=stream_data
    )
