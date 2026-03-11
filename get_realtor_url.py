import requests
import json

REALTOR_API = "https://api2.realtor.ca/Listing.svc/PropertySearch_Post"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://www.realtor.ca",
    "Referer": "https://www.realtor.ca/"
}

payload = {
    "ZoomLevel": "12",
    "LatitudeMax": "43.75027",
    "LatitudeMin": "43.61529",
    "LongitudeMax": "-79.27005",
    "LongitudeMin": "-79.50763",
    "Sort": "6-D",
    "PropertyTypeGroupID": "1",
    "TransactionTypeId": "2",
    "PropertySearchTypeId": "0",
    "Currency": "CAD",
    "RecordsPerPage": "5",
    "ApplicationId": "1",
    "CultureId": "1",
    "Version": "7.0",
    "CurrentPage": "1",
}

try:
    response = requests.post(REALTOR_API, data=payload, headers=HEADERS)
    data = response.json()
    for item in data.get('Results', []):
        print(f"https://www.realtor.ca{item.get('RelativeDetailsURL', '')}")
except Exception as e:
    print(f"Error: {e}")
