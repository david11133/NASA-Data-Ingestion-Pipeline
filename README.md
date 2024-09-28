# NASA NEO Data Engineering Project

> **⚠️ Note:** This project is currently under development. Features and functionalities are still being added, and the structure may change.

## Overview

This project involves fetching data about near-Earth objects (NEOs) from NASA's NEO API, streaming it to Kafka, and processing it using Apache Spark, with the final goal of storing the data in Cassandra. The project is structured to facilitate easy maintenance and scalability.

## Project Structure
```graphql
NASA-Data-Ingestion-Pipeline/
│
├── dags/                           # Airflow DAGs
│   └── nasa_neo_data_fetcher.py   # Main Airflow DAG for fetching data
│
├── kafka/                          # Kafka producer and consumer scripts
│   ├── producer.py                 # Kafka producer script
│   └── consumer.py                 # Kafka consumer script using Spark
|
├── dbt/
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

## Technologies Used

- **Apache Airflow**: For orchestrating the data pipeline.
- **Apache Kafka**: For streaming data between components.
- **Apache Spark**: For processing the streamed data.
- **Cassandra**: For storing processed data.
- **Python**: The primary programming language used.

## Setup Instructions

### Prerequisites

- Docker and Docker Compose installed on your machine.
- A valid NASA API key to access the NEO API.

### Running the Project

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/david11133/NASA-Data-Ingestion-Pipeline
   cd NASA-Data-Ingestion-Pipeline
   ```

2. **Start Services**:
   Use Docker Compose to start all required services (Airflow, Kafka, Zookeeper, and Cassandra).
   ```bash
   docker-compose up
   ```

3. **Access Airflow**:
   - Open your web browser and go to `http://localhost:8080`.
   - You can find your Airflow DAG named `nasa_neo_data_fetcher`.

4. **Run the Airflow DAG**:
   - Trigger the DAG to start fetching data from the NASA NEO API and stream it to Kafka.

5. **Run the Kafka Consumer**:
   - Open a new terminal and run the consumer script to process the streamed data.
   ```bash
   python kafka/consumer.py
   ```

### Kafka Producer Example

You can test sending data to Kafka using the producer script.

1. **Run the Producer**:
   Open a new terminal and execute:
   ```bash
   python kafka/producer.py
   ```

## Next Steps

1. Implement logic in the Kafka consumer to process data and store it in Cassandra.
2. Set up appropriate CQL scripts to create the necessary tables in Cassandra.
3. Explore additional features like error handling and monitoring.

## License

This project is licensed under the MIT License.

## Contact

For any questions or contributions, please reach out to [davidnady4yad@gmail.com].