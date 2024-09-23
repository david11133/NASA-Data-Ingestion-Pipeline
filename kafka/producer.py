from kafka import KafkaProducer
import json
import uuid
import time

def create_producer():
    """Create a Kafka producer."""
    return KafkaProducer(
        bootstrap_servers='broker:9092',  # Adjust as necessary
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

def send_data(producer, topic, data):
    """Send data to the specified Kafka topic."""
    for item in data:
        producer.send(topic, value=item)
        print(f"Sent: {item}")  # Optional logging
        time.sleep(1)  # Adjust delay as necessary

if __name__ == "__main__":
    producer = create_producer()
    topic = 'nasa_neo_data'  # Specify your Kafka topic

    
    data = [
        {
            'id': str(uuid.uuid4()),
            'name': 'Asteroid A',
            'is_potentially_hazardous': True,
            'estimated_diameter': {
                'min_meters': 150,
                'max_meters': 300
            },
            'close_approach_date': '2024-09-21',
            'miss_distance_km': '120000',
            'relative_velocity_kmh': '25000'
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'Asteroid B',
            'is_potentially_hazardous': False,
            'estimated_diameter': {
                'min_meters': 80,
                'max_meters': 150
            },
            'close_approach_date': '2024-09-22',
            'miss_distance_km': '300000',
            'relative_velocity_kmh': '20000'
        }
    ]

send_data(producer, topic, data)
producer.flush()
producer.close()
