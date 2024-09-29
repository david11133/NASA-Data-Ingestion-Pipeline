from kafka import KafkaProducer
import os
import json

def send_data_to_kafka(data):
    producer = KafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BROKER"),  # Load Kafka broker from env
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    topic = os.getenv("KAFKA_TOPIC")  # Load topic from env
    producer.send(topic, value=data)
    producer.flush()
    producer.close()
