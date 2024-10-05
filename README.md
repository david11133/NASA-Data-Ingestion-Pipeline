<p align="center">
<img height="150" width="150" src="https://cdn.icon-icons.com/icons2/2699/PNG/512/nasa_logo_icon_170926.png"/>
</p>

<h1 align="center">NASA NEO Data Engineering Project</h1>

> [!NOTE]
> This project is currently under development. Features and functionalities are still being added, and the structure may change.

## Overview

This project demonstrates a real-time data streaming and processing pipeline using NASA's NEOWS (Near Earth Object Web Service) APIs to generate dynamic data on near-Earth objects. A Python script fetches data from the NEOWS APIs, publishing it to a Kafka topic for efficient management. We orchestrate this process with Apache Airflow, scheduling the data generation script to run regularly. Spark Structured Streaming is then utilized to consume and modify the data from Kafka, which is ultimately stored in a Cassandra database. All components run within Docker containers, ensuring a consistent and scalable development environment.

## Data Architecture

![System Architecture](https://github.com/david11133/NASA-Data-Ingestion-Pipeline/blob/main/docs/data%20architecture.drawio.svg)

## Project Structure
```graphql
NASA-Data-Ingestion-Pipeline/
│
├── airflow/
│   ├── dags/
│   │   ├── nasa_kafka_stream.py         # Airflow DAG for Kafka streaming
│   ├── scripts/
│   │   └── entrypoint.sh                # Entrypoint for Airflow Docker container 
|   └── .env
│
├── kafka/
|   ├── .env                       # Kafka configuration
│   ├── consumer.py                # Kafka consumer script          
│   └── producer.py                # Kafka producer script for user data                           
│
├── spark/
│   ├── scripts/
│   │   └── spark_stream.py              # Spark streaming job
│   ├── config/
│   │   └── spark-defaults.conf          # Spark defaults
│   └── examples/
│       └── example_spark_job.py         # Example Spark job
│
├── requirements.txt                      # Python dependencies for Airflow
│
├── docker-compose.yml                    # Docker Compose file for services
│
├── docs/
│   ├── architecture.md                  # Overview of system architecture
│   ├── setup_guide.md                   # Instructions for setting up the project
│   ├── api_documentation.md             # API details for the user data endpoint
│   └── technology_overview.md           # Descriptions of all technologies used
│
└── README.md                            # Main project overview and instructions

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
