# NASA NEO Data Engineering Project

## Overview

This project involves fetching data about near-Earth objects (NEOs) from NASA's NEO API, streaming it to Kafka, and processing it using Apache Spark, with the final goal of storing the data in Cassandra. The project is structured to facilitate easy maintenance and scalability.

## Project Structure
```graphql
my_data_engineering_project/
│
├── dags/                           # Airflow DAGs
│   └── nasa_neo_data_fetcher.py   # Main Airflow DAG for fetching data
│
├── kafka/                          # Kafka producer and consumer scripts
│   ├── producer.py                 # Kafka producer script
│   └── consumer.py                 # Kafka consumer script using Spark
│
├── spark/                          # Spark streaming jobs
│   └── streaming_job.py            # Spark streaming job for processing data
│
├── cassandra/                      # Cassandra setup scripts
│   ├── create_keyspace.cql         # CQL script to create Cassandra keyspace
│   └── create_table.cql            # CQL script to create necessary tables
│
├── requirements.txt                # Python dependencies
│
├── scripts/                        # Utility scripts
│   └── entrypoint.sh               # Entry point script for Airflow (if needed)
│
├── README.md                       # Project overview and instructions
│
└── docker-compose.yml              # Docker Compose configuration
```