import requests
import time
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

API_URL = "http://localhost:8000"

def test_listing_agent():
    logging.info("Starting Listing Agent Test...")
    
    # 1. Start the agent
    logging.info("Calling /agent/start...")
    res = requests.post(f"{API_URL}/agent/start", json={
        "criteria": {
            "cities": ["toronto"],
            "min_price": 500000,
            "max_price": 2000000,
            "sources": ["zoocasa"]  # Use zoocasa for quick test
        },
        "interval_minutes": 1
    })
    print("Start Response:", json.dumps(res.json(), indent=2))
    
    # 2. Check status
    logging.info("Calling /agent/status...")
    res = requests.get(f"{API_URL}/agent/status")
    print("Status:", json.dumps(res.json(), indent=2))
    
    # 3. Wait a bit for scraping to happen
    logging.info("Waiting 15 seconds for agent to scrape...")
    time.sleep(15)
    
    # 4. Check status again
    res = requests.get(f"{API_URL}/agent/status")
    status = res.json()
    print("Status after 15s:", json.dumps(status, indent=2))
    
    # 5. Get alerts
    logging.info("Getting alerts...")
    res = requests.get(f"{API_URL}/agent/alerts")
    alerts = res.json().get("alerts", [])
    print(f"Total alerts found: {len(alerts)}")
    if alerts:
        print("Latest alert:", json.dumps(alerts[0].get("listing", {}).get("address"), indent=2))
        
    # 6. Stop the agent
    logging.info("Stopping agent...")
    res = requests.post(f"{API_URL}/agent/stop")
    print("Stop Response:", json.dumps(res.json(), indent=2))

if __name__ == "__main__":
    test_listing_agent()
