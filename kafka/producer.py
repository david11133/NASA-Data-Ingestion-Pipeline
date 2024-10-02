import os
import json
import requests
from kafka import KafkaProducer
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

# Configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
NASA_API_KEY = os.getenv("NASA_API_KEY")

# Initialize Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def fetch_nasa_neo_data():
    start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={start_date}&end_date={start_date}&api_key={NASA_API_KEY}"

    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad responses
    data = response.json()

    return data['near_earth_objects']

def format_and_send_data():
    neos = fetch_nasa_neo_data()
    for date, asteroids in neos.items():
        for asteroid in asteroids:
            important_data = {
                "date": date,
                "id": asteroid["id"],
                "name": asteroid["name"],
                "estimated_diameter": {
                    "min": asteroid["estimated_diameter"]["kilometers"]["estimated_diameter_min"],
                    "max": asteroid["estimated_diameter"]["kilometers"]["estimated_diameter_max"]
                },
                "is_potentially_hazardous": asteroid["is_potentially_hazardous_asteroid"],
                "close_approach_date": asteroid["close_approach_data"][0]["close_approach_date"],
                "relative_velocity": asteroid["close_approach_data"][0]["relative_velocity"]["kilometers_per_second"],
                "miss_distance": asteroid["close_approach_data"][0]["miss_distance"]["kilometers"]
            }
            producer.send(KAFKA_TOPIC, value=important_data)
            producer.flush()
            print(f"Sent data to Kafka: {important_data}")

if __name__ == "__main__":
    format_and_send_data()
