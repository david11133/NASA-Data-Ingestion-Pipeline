from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
import requests
import json
import os

# Function to fetch NASA NEO data
def fetch_nasa_neo_data():
    api_key = os.getenv("NASA_API_KEY")  # Load from environment variable
    start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")  # Fetch data for yesterday
    end_date = start_date
    url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={start_date}&end_date={end_date}&api_key={api_key}"

    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        important_data = []
        
        for date, asteroids in data['near_earth_objects'].items():
            for asteroid in asteroids:
                important_data.append({
                    "Date": date,
                    "ID": asteroid["id"],
                    "Name": asteroid["name"],
                    "Estimated Diameter (km)": {
                        "min": asteroid["estimated_diameter"]["kilometers"]["estimated_diameter_min"],
                        "max": asteroid["estimated_diameter"]["kilometers"]["estimated_diameter_max"]
                    },
                    "Is Potentially Hazardous": asteroid["is_potentially_hazardous_asteroid"],
                    "Close Approach Date": asteroid["close_approach_data"][0]["close_approach_date"],
                    "Relative Velocity (km/s)": asteroid["close_approach_data"][0]["relative_velocity"]["kilometers_per_second"],
                    "Miss Distance (km)": asteroid["close_approach_data"][0]["miss_distance"]["kilometers"]
                })
        
        print(json.dumps(important_data, indent=4))  # Print or save data as needed
    else:
        print("Error fetching data:", response.status_code)

# Define default arguments
default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 9, 29),  # Change to your desired start date
}

# Define the DAG
dag = DAG(
    'nasa_neo_data_fetcher',
    default_args=default_args,
    description='Fetch NASA NEO data daily',
    schedule_interval=timedelta(days=1),  # Run daily
)

# Define the task
fetch_task = PythonOperator(
    task_id='fetch_nasa_data',
    python_callable=fetch_nasa_neo_data,
    dag=dag,
)

fetch_task
