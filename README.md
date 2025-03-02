<p align="center">
<img height="150" width="150" src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/NASA_logo.svg/2449px-NASA_logo.svg.png"/>
</p>

<h1 align="center">NASA NEO Data Engineering Project</h1>

> [!NOTE]
> This project is currently under development. Features and functionalities are still being added, and the structure may change.

## 💡 Overview
This project demonstrates a real-time data streaming and processing pipeline using NASA's NEOWS (Near Earth Object Web Service) APIs to generate dynamic data on near-Earth objects. A Python script fetches data from the NEOWS APIs, publishing it to a Kafka topic for efficient management. We orchestrate this process with Apache Airflow, scheduling the data generation script to run regularly. Spark Structured Streaming is then utilized to consume and modify the data from Kafka, which is ultimately stored in a Cassandra database. All components run within Docker containers, ensuring a consistent and scalable development environment.

## 📜 Scenario
This project utilizes a database of near-Earth objects (NEOs) sourced from NASA's NEOWS APIs. The database is regularly updated with real-time data on NEOs, including their trajectories and potential hazards. To ensure the data is actionable, it requires automated cleaning and transformation processes to convert it into usable formats with minimal human intervention. The goal is to facilitate continuous monitoring and analysis, providing valuable insights into the risks posed by these celestial objects.

## 📊 Data
The data for this project is sourced from NASA's NEOWS APIs, which provide extensive information on near-Earth objects.

```json
{
    "Date": "2024-09-27",
    "ID": "54483136",
    "Name": "(2024 SY2)",
    "Estimated Diameter (km)": {
        "min": 0.0173362426,
        "max": 0.038765017
    },
    "Is Potentially Hazardous": false,
    "Close Approach Date": "2024-09-27",
    "Relative Velocity (km/s)": "8.7240830597",
    "Miss Distance (km)": "7580603.623832072"
}
```
  

## 🏗️ Data Architecture
![System Architecture](https://github.com/david11133/NASA-Data-Ingestion-Pipeline/raw/main/docs/data%20architecture.drawio.svg)

## 🛠 Technologies Used
- Cloud - [**AWS**](https://aws.amazon.com/)
- Containerization - [**Docker**](https://www.docker.com), [**Docker Compose**](https://docs.docker.com/compose/)
- Stream Processing - [**Kafka**](https://kafka.apache.org)
- Orchestration - [**Airflow**](https://airflow.apache.org)
- Transformation - [**Spark**](https://spark.apache.org)
- Data Lake - [**Cassandra**](https://cassandra.apache.org/_/index.html)
- Language - [**Python**](https://www.python.org)

## 🔧 Project Structure

```graphql
NASA-Data-Ingestion-Pipeline/

│
├── airflow/
│   ├── dags/
│   │   ├── nasa_kafka_stream.py         # Airflow DAG for Kafka streaming
│   ├── scripts/
│   │   └── entrypoint.sh                # Entrypoint for Airflow Docker container
│   └── .env
│
├── spark/
│   ├── scripts/
│   │   └── spark_stream.py              # Spark streaming job
│   ├── config/
│   │   └── spark-defaults.conf          # Spark defaults
│   └── examples/
│       └── example_spark_job.py         # Example Spark job
│
├── requirements.txt                      # Python dependencies for Airflow
│
├── docker-compose.yml                    # Docker Compose file for services
│
├── docs/
│   ├── architecture.md                  # Overview of system architecture
│   ├── setup_guide.md                   # Instructions for setting up the project
│   ├── api_documentation.md             # API details for the user data endpoint
│   └── technology_overview.md           # Descriptions of all technologies used
│
└── README.md                            # Main project overview and instructions
```

##  Getting Started
1. Clone the repository:
    ```bash
    git clone https://github.com/david11133/NASA-Data-Ingestion-Pipeline
    ```

2. Navigate to the project directory:
    ```bash
    cd NASA-Data-Ingestion-Pipeline
    ```

3. Run Docker Compose to spin up the services:
    ```bash
    docker-compose up
    ```

## 🌐 Contact
For any questions or contributions, please reach out to [davidnady4yad@gmail.com].
