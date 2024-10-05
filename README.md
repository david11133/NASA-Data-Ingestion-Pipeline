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

## Technologies Used

- **Apache Airflow**: For orchestrating the data pipeline.
- **Apache Kafka**: For streaming data between components.
- **Apache Spark**: For processing the streamed data.
- **Cassandra**: For storing processed data.
- **Python**: The primary programming language used.
  
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


## Contact

For any questions or contributions, please reach out to [davidnady4yad@gmail.com].
