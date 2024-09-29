import requests
import json

# Step 1: Set up the API URL and key
api_key = "wSJjaC224VWXNgCnlzpWSpODlYNyfdeNzUMRRjBU"  # Replace with your actual API key
start_date = "2024-09-27"
end_date = "2024-09-27"
url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={start_date}&end_date={end_date}&api_key={api_key}"

# Step 2: Fetch data from the NEO API
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    data = response.json()
    print("Data fetched successfully!")
    
    for date, asteroids in data['near_earth_objects'].items():
        for asteroid in asteroids:
            # Extract important data
            important_data = {
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
            }
            print(json.dumps(important_data, indent=4))  # Pretty print the important data
else:
    print("Error fetching data:", response.status_code)
