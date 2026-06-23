import requests

def verify():
    login_url = "http://localhost:8000/api/token/"
    credentials = {
        "username": "admin",
        "password": "admin123"
    }
    
    print("Logging in...")
    r = requests.post(login_url, json=credentials)
    if r.status_code != 200:
        print(f"Failed to login: {r.status_code} - {r.text}")
        return
    
    token = r.json().get("access")
    print("Logged in successfully.")
    
    # Fetch historical telemetry
    historical_url = "http://localhost:8000/api/telemetry/historical/?range=7days"
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Fetching historical telemetry from: {historical_url}")
    r = requests.get(historical_url, headers=headers)
    print(f"Fetch historical status: {r.status_code}")
    
    if r.status_code == 200:
        res = r.json()
        print("\nSUCCESS: Historical telemetry API responded 200!")
        print(f"Total records analyzed: {res.get('total_records_analyzed')}")
        print(f"Total visitors estimated: {res.get('total_visitors_estimated')}")
        print(f"Peak hour: {res.get('peak_hour')}")
        print(f"Busiest sector: {res.get('busiest_sector')}")
        print("Queue metrics:")
        print(f"  avg_people_in_queue: {res.get('queue_metrics', {}).get('avg_people_in_queue')}")
        print(f"  avg_wait_time_seconds: {res.get('queue_metrics', {}).get('avg_wait_time_seconds')}")
        print(f"  max_wait_time_seconds: {res.get('queue_metrics', {}).get('max_wait_time_seconds')}")
        print(f"  saturation_percentage: {res.get('queue_metrics', {}).get('saturation_percentage')}")
        print(f"Sectors metrics keys: {list(res.get('sectors_metrics', {}).keys())}")
        print(f"Hourly inflow samples: {len(res.get('hourly_inflow', []))}")
        print(f"Daily inflow samples: {len(res.get('daily_inflow', []))}")
        
        # Now check 30 days
        historical_url_30 = "http://localhost:8000/api/telemetry/historical/?range=30days"
        print(f"\nFetching historical telemetry from: {historical_url_30}")
        r30 = requests.get(historical_url_30, headers=headers)
        print(f"Fetch historical (30 days) status: {r30.status_code}")
        if r30.status_code == 200:
            res30 = r30.json()
            print("SUCCESS: 30 days telemetry API responded 200!")
            print(f"Total records analyzed: {res30.get('total_records_analyzed')}")
    else:
        print(f"Failed to fetch historical telemetry: {r.text}")

if __name__ == "__main__":
    verify()
