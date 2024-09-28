from kafka import KafkaProducer
import json
import requests
import os
import time

def create_producer():
    """Create a Kafka producer."""
    kafka_broker = os.getenv('KAFKA_BROKER_URL', '54.169.164.92:9092')  # Replace with your EC2 public DNS or IP
    return KafkaProducer(
        bootstrap_servers=kafka_broker,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

def fetch_data(api_key, start_date, end_date):
    """Fetch asteroid data from NASA's NEO API."""
    url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={start_date}&end_date={end_date}&api_key={api_key}"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()['near_earth_objects']
    else:
        print(f"Error fetching data: {response.status_code}")
        return []

def send_data(producer, topic, data):
    """Send data to the specified Kafka topic."""
    for item in data:
        try:
            producer.send(topic, value=item)
            print(f"Sent: {item}")  # Optional logging
            time.sleep(1)  # Adjust delay as necessary
        except Exception as e:
            print(f"Error sending message: {e}")

if __name__ == "__main__":
    api_key = os.getenv('NASA_API_KEY')  # Get API key from environment variable
    producer = create_producer()
    topic = 'nasa_neo_data'  # Specify your Kafka topic

    # Specify date range for fetching data
    start_date = '2024-09-21'
    end_date = '2024-09-21'

    # Fetch data from the API
    asteroid_data = fetch_data(api_key, start_date, end_date)

    # Send the fetched data to Kafka
    if asteroid_data:
        send_data(producer, topic, asteroid_data)

    producer.flush()
    producer.close()
