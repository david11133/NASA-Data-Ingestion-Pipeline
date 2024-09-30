from kafka import KafkaProducer
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def send_data_to_kafka(data):
    kafka_broker = os.getenv("KAFKA_BROKER")
    kafka_topic = os.getenv("KAFKA_TOPIC")
    
    if not kafka_broker or not kafka_topic:
        logging.error("KAFKA_BROKER or KAFKA_TOPIC environment variable not set.")
        return

    producer = KafkaProducer(
        bootstrap_servers=kafka_broker,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        acks='all'  # Wait for all replicas to acknowledge
    )
    
    try:
        producer.send(kafka_topic, value=data)
        producer.flush()
        logging.info(f"Data sent to Kafka topic '{kafka_topic}': {data}")
    except Exception as e:
        logging.error(f"Failed to send data to Kafka: {e}")
    finally:
        producer.close()
