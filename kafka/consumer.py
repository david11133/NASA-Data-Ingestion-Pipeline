from kafka import KafkaConsumer
import json
import os
import signal
import sys

def create_consumer(topic):
    """Create a Kafka consumer."""
    return KafkaConsumer(
        topic,
        bootstrap_servers=os.getenv('KAFKA_BROKER_URL', 'broker:9092'),  # Use environment variable
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='my-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

def signal_handler(sig, frame):
    """Handle shutdown signal."""
    print('Shutting down consumer...')
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C
    topic = 'nasa_neo_data'  # Specify your Kafka topic
    consumer = create_consumer(topic)

    print(f"Listening for messages on topic: {topic}")

    for message in consumer:
        try:
            asteroid_data = message.value
            print(f"Received: {asteroid_data}")
            # You can add further processing here if needed
        except Exception as e:
            print(f"Error processing message: {e}")
