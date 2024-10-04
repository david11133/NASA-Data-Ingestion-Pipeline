import os
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, json_tuple
from pyspark.sql.types import StructType, StructField, StringType, BooleanType

# Set up logging
logging.basicConfig(level=logging.INFO)

def main():
    # Create Spark session
    spark = SparkSession.builder \
        .appName("Kafka Consumer Spark") \
        .getOrCreate()

    # Load Kafka parameters from environment variables
    kafka_broker = os.getenv("KAFKA_BROKER", "localhost:9092")  # Fallback to localhost if not set
    kafka_topic = os.getenv("KAFKA_TOPIC", "your_kafka_topic")  # Fallback to a default topic

    # Read data from Kafka
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_broker) \
        .option("subscribe", kafka_topic) \
        .load()

    # Deserialize JSON data from Kafka
    value_df = df.selectExpr("CAST(value AS STRING)")

    # Define schema for the expected data
    schema = StructType([
        StructField("Date", StringType(), True),
        StructField("ID", StringType(), True),
        StructField("Name", StringType(), True),
        StructField("Estimated Diameter (km)", StringType(), True),
        StructField("Is Potentially Hazardous", BooleanType(), True),
        StructField("Close Approach Date", StringType(), True),
        StructField("Relative Velocity (km/s)", StringType(), True),
        StructField("Miss Distance (km)", StringType(), True)
    ])

    # Process the JSON data (assuming the incoming data is JSON formatted)
    processed_df = value_df.select(
        json_tuple("value", "Date", "ID", "Name", "Estimated Diameter (km)", "Is Potentially Hazardous", 
                   "Close Approach Date", "Relative Velocity (km/s)", "Miss Distance (km)")
    ).toDF("Date", "ID", "Name", "Estimated Diameter (km)", "Is Potentially Hazardous", 
           "Close Approach Date", "Relative Velocity (km/s)", "Miss Distance (km)")

    # Cast the "Is Potentially Hazardous" field to Boolean
    processed_df = processed_df.withColumn("Is Potentially Hazardous", col("Is Potentially Hazardous").cast(BooleanType()))

    # Example transformation: Filter hazardous asteroids
    hazardous_df = processed_df.filter(col("Is Potentially Hazardous") == True)

    # Write the output to the console (for testing)
    query = hazardous_df.writeStream \
        .outputMode("append") \
        .format("console") \
        .start()

    logging.info(f"Listening for messages on topic: {kafka_topic} from broker: {kafka_broker}")
    query.awaitTermination()

if __name__ == "__main__":
    main()
