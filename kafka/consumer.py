import os
import json
from kafka import KafkaConsumer
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")

# Initialize Kafka consumer
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    auto_offset_reset='earliest',
    enable_auto_commit=True,
)

if __name__ == "__main__":
    print(f"Listening for messages on topic: {KAFKA_TOPIC}")
    for message in consumer:
        data = message.value
        # Here, you can implement any processing logic for the received data
        print(f"Received NEO Data: ID: {data['id']}, Name: {data['name']}, Close Approach Date: {data['close_approach_date']}")
