from kafka import KafkaConsumer
import os
import json

def consume_data():
    consumer = KafkaConsumer(
        os.getenv("KAFKA_TOPIC"),
        bootstrap_servers=os.getenv("KAFKA_BROKER"),
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=True
    )
    
    for message in consumer:
        print(f"Received message: {message.value}")
