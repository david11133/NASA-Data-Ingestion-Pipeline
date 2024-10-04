from pyspark.sql import SparkSession
from pyspark.sql.functions import col, json_tuple

def main():
    # Create Spark session
    spark = SparkSession.builder \
        .appName("Kafka Consumer Spark") \
        .getOrCreate()

    # Define Kafka parameters
    kafka_broker = "KAFKA_BROKER:9092"  # Replace with your Kafka broker
    kafka_topic = "KAFKA_TOPIC"          # Replace with your topic name

    # Read data from Kafka
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_broker) \
        .option("subscribe", kafka_topic) \
        .load()

    # Deserialize JSON data from Kafka
    value_df = df.selectExpr("CAST(value AS STRING)")

    # Process the JSON data (assuming the incoming data is JSON formatted)
    processed_df = value_df.select(
        json_tuple("value", "Date", "ID", "Name", "Estimated Diameter (km)", "Is Potentially Hazardous", "Close Approach Date", "Relative Velocity (km/s)", "Miss Distance (km)")
    ).toDF("Date", "ID", "Name", "Estimated Diameter (km)", "Is Potentially Hazardous", "Close Approach Date", "Relative Velocity (km/s)", "Miss Distance (km)")

    # Example transformation: Filter hazardous asteroids
    hazardous_df = processed_df.filter(col("Is Potentially Hazardous") == 'true')

    # Write the output to the console (for testing)
    query = hazardous_df.writeStream \
        .outputMode("append") \
        .format("console") \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    main()
