from kafka import KafkaConsumer
import os
import json
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)

def consume_data():
    kafka_topic = os.getenv("KAFKA_TOPIC")
    kafka_broker = os.getenv("KAFKA_BROKER")
    
    if not kafka_topic or not kafka_broker:
        logging.error("KAFKA_TOPIC or KAFKA_BROKER environment variable not set.")
        sys.exit(1)

    consumer = KafkaConsumer(
        kafka_topic,
        bootstrap_servers=kafka_broker,
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=True
    )

    try:
        logging.info(f"Listening for messages on topic: {kafka_topic}")
        for message in consumer:
            logging.info(f"Received message: {message.value}")
    except Exception as e:
        logging.error(f"Error while consuming messages: {e}")
    finally:
        consumer.close()
        logging.info("Consumer closed.")

if __name__ == "__main__":
    consume_data()
