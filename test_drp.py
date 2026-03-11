from DrissionPage import ChromiumPage, ChromiumOptions
import time
import json

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
payload_str = "&".join(f"{k}={v}" for k, v in payload.items())

def main():
    co = ChromiumOptions()
    co.headless(True)  # Native bypass works in headless usually! But let's verify
    # Use user's edge just in case
    co.set_browser_path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    
    page = ChromiumPage(co)
    
    # Listen to XHR traffic naturally
    page.listen.start('Listing.svc/PropertySearch_Post')
    
    # Navigate to map
    page.get("https://www.realtor.ca/map", retry=1, interval=1, timeout=10)
    time.sleep(5)
    
    # Intercept naturally triggered requests or inject a script
    fetch_js = f"""
    fetch('https://api2.realtor.ca/Listing.svc/PropertySearch_Post', {{
        method: 'POST',
        body: '{payload_str}',
        headers: {{
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01'
        }},
        credentials: 'omit'
    }})
    .then(response => response.text())
    .then(data => window.__drission_data = data)
    .catch(err => window.__drission_data = "ERROR: " + err.message);
    """
    
    # Before fetch, wait for Incapsula challenge if any
    print("Page title:", page.title)
    
    page.run_js(fetch_js)
    res = None
    for _ in range(10):
        res = page.run_js("return window.__drission_data;")
        if res:
            break
        time.sleep(1)
        
    if res and not str(res).startswith("ERROR"):
        try:
            data = json.loads(res)
            print("Found results:", len(data.get("Results", [])))
        except:
            print("Failed JSON parse:", str(res)[:200])
    else:
        print("Fetch failed or error:", res)
        
    page.quit()

if __name__ == "__main__":
    main()
