from kafka import KafkaConsumer
import json

def create_consumer(topic):
    """Create a Kafka consumer."""
    return KafkaConsumer(
        topic,
        bootstrap_servers='broker:9092',  # Adjust as necessary
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='my-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

if __name__ == "__main__":
    topic = 'nasa_neo_data'  # Specify your Kafka topic
    consumer = create_consumer(topic)

    print(f"Listening for messages on topic: {topic}")

    for message in consumer:
        # Process the message
        asteroid_data = message.value
        print(f"Received: {asteroid_data}")

