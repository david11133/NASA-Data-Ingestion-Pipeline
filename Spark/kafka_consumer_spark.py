import logging
from cassandra.cluster import Cluster
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, BooleanType, FloatType

# Set up logging
logging.basicConfig(level=logging.INFO)

def create_keyspace(session):
    session.execute("""
        CREATE KEYSPACE IF NOT EXISTS neo_data
        WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'};
    """)
    logging.info("Keyspace created successfully!")

def create_table(session):
    session.execute("""
    CREATE TABLE IF NOT EXISTS neo_data.near_earth_objects (
        id UUID PRIMARY KEY,
        date TEXT,
        name TEXT,
        estimated_diameter_min FLOAT,
        estimated_diameter_max FLOAT,
        is_potentially_hazardous BOOLEAN,
        close_approach_date TEXT,
        relative_velocity FLOAT,
        miss_distance FLOAT
    );
    """)
    logging.info("Table created successfully!")

def insert_data(session, **kwargs):
    logging.info("Inserting data...")
    try:
        session.execute("""
            INSERT INTO neo_data.near_earth_objects(id, date, name, estimated_diameter_min, 
                estimated_diameter_max, is_potentially_hazardous, close_approach_date, 
                relative_velocity, miss_distance)
                VALUES (uuid(), %s, %s, %s, %s, %s, %s, %s, %s)
        """, (kwargs['date'], kwargs['name'], kwargs['estimated_diameter_min'],
              kwargs['estimated_diameter_max'], kwargs['is_potentially_hazardous'],
              kwargs['close_approach_date'], kwargs['relative_velocity'], kwargs['miss_distance']))
        logging.info(f"Data inserted for {kwargs['name']} on {kwargs['date']}")
    except Exception as e:
        logging.error(f'Could not insert data due to: {e}')

def create_spark_connection():
    s_conn = None
    try:
        s_conn = SparkSession.builder \
            .appName('NEODataStreaming') \
            .config('spark.jars.packages', "com.datastax.spark:spark-cassandra-connector_2.13:3.4.1," 
                                           "org.apache.spark:spark-sql-kafka-0-10_2.13:3.4.1") \
            .config('spark.cassandra.connection.host', 'localhost') \
            .getOrCreate()
        s_conn.sparkContext.setLogLevel("ERROR")
        logging.info("Spark connection created successfully!")
    except Exception as e:
        logging.error(f"Couldn't create the Spark session due to: {e}")
    return s_conn

def connect_to_kafka(spark_conn):
    spark_df = None
    try:
        spark_df = spark_conn.readStream \
            .format('kafka') \
            .option('kafka.bootstrap.servers', 'localhost:9092') \
            .option('subscribe', 'nasa_neo_data') \
            .option('startingOffsets', 'earliest') \
            .load()
        logging.info("Kafka DataFrame created successfully")
    except Exception as e:
        logging.warning(f"Kafka DataFrame could not be created because: {e}")
    return spark_df

def create_cassandra_connection():
    try:
        cluster = Cluster(['localhost'])
        return cluster.connect()
    except Exception as e:
        logging.error(f"Could not create Cassandra connection due to: {e}")
        return None

def create_selection_df_from_kafka(spark_df):
    schema = StructType([
        StructField("date", StringType(), False),
        StructField("name", StringType(), False),
        StructField("estimated_diameter_min", FloatType(), False),
        StructField("estimated_diameter_max", FloatType(), False),
        StructField("is_potentially_hazardous", BooleanType(), False),
        StructField("close_approach_date", StringType(), False),
        StructField("relative_velocity", FloatType(), False),
        StructField("miss_distance", FloatType(), False)
    ])
    
    sel = spark_df.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col('value'), schema).alias('data')).select("data.*")
    
    logging.info("Selection DataFrame created successfully.")
    return sel

if __name__ == "__main__":
    # Create Spark connection
    spark_conn = create_spark_connection()

    if spark_conn is not None:
        # Connect to Kafka with Spark connection
        spark_df = connect_to_kafka(spark_conn)
        selection_df = create_selection_df_from_kafka(spark_df)
        
        # Create Cassandra connection
        session = create_cassandra_connection()

        if session is not None:
            create_keyspace(session)
            create_table(session)

            logging.info("Streaming is being started...")

            # Write the DataFrame to Cassandra
            streaming_query = (selection_df.writeStream
                               .foreachBatch(lambda batch_df, _: batch_df.foreach(lambda row: insert_data(session, **row.asDict())))
                               .outputMode("update")
                               .start())

            streaming_query.awaitTermination()
