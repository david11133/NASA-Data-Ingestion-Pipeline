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
    
    # Step 3: Display the full data for each near-Earth object
    print("Data fetched successfully!")
    
    for date, asteroids in data['near_earth_objects'].items():
        print(f"\nDate: {date}")
        for asteroid in asteroids:
            # Print the entire asteroid data
            print(json.dumps(asteroid, indent=4))  # Pretty print the JSON data
else:
    print("Error fetching data:", response.status_code)