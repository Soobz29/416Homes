import sys
try:
    import distutils
except ImportError:
    import setuptools._distutils as distutils
    sys.modules['distutils'] = distutils
    sys.modules['distutils.version'] = distutils.version

import undetected_chromedriver as uc
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
    options = uc.ChromeOptions()
    # uc works best without explicit headless flag first, but let's try headless=new
    options.headless = True
    options.add_argument('--headless=new')
    
    driver = uc.Chrome(options=options)
    
    try:
        driver.get("https://www.realtor.ca/map")
        time.sleep(5)
        print("Title:", driver.title)
        
        fetch_js = f"""
        var done = arguments[0];
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
        .then(data => done(data))
        .catch(err => done("ERROR: " + err.message));
        """
        
        driver.set_script_timeout(30)
        res = driver.execute_async_script(fetch_js)
        
        if res and not res.startswith("ERROR"):
            try:
                data = json.loads(res)
                print("Found results:", len(data.get("Results", [])))
            except:
                print("Failed JSON parse:", res[:200])
        else:
            print("Fetch failed or error:", res)
            
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
