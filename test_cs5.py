import cloudscraper

payload = {
    "ZoomLevel": "13",
    "LatitudeMax": "43.9560",
    "LatitudeMin": "43.5290",
    "LongitudeMax": "-79.1169",
    "LongitudeMin": "-79.8440",
    "Sort": "6-D",
    "PropertyTypeGroupID": "1",
    "TransactionTypeId": "2",
    "PropertySearchTypeId": "0",
    "Currency": "CAD",
    "RecordsPerPage": "50",
    "ApplicationId": "1",
    "CultureId": "1",
    "Version": "7.0",
    "CurrentPage": "1",
}

def main():
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.realtor.ca",
        "Referer": "https://www.realtor.ca/",
    }
    
    print("Testing cloudscraper...")
    response = scraper.post('https://api2.realtor.ca/Listing.svc/PropertySearch_Post', data=payload, headers=headers)
    print("Status code:", response.status_code)
    try:
        data = response.json()
        print("Success! Listings:", len(data.get("Results", [])))
    except:
        print("Failed. First 200 chars:", response.text[:200])

if __name__ == "__main__":
    main()
