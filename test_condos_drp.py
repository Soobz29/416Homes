from DrissionPage import ChromiumPage, ChromiumOptions
import time
import json

def main():
    co = ChromiumOptions()
    co.headless(False)
    co.set_browser_path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    
    page = ChromiumPage(co)
    page.listen.start('condos.ca/api/listings')
    
    print("Navigating to Condos.ca map...")
    page.get("https://condos.ca/toronto/condos-for-sale", retry=1, interval=1, timeout=15)
    
    # Wait for the map and Challenge
    time.sleep(15)
    print("Page title after 15s:", page.title)
    
    # Listen for intercepted APIs
    res = page.listen.wait(timeout=5)
    if res:
        try:
            print("API Intercepted! URL:", res.url)
            print("API Status:", res.response.status)
            data = res.response.body
            
            if isinstance(data, dict):
                results = data.get('results', []) or data.get('listings', [])
                print("Found listings API response! Count:", len(results))
            else:
                data = json.loads(data)
                results = data.get('results', []) or data.get('listings', [])
                print("Found listings API response! Count:", len(results))
        except Exception as e:
            print("Failed parsing captured API:", e)
    else:
        print("No API captured")
        
        # Scrape DOM as fallback
        html = page.html
        with open("condos_dom.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Wrote DOM to condos_dom.html")
        
    page.quit()

if __name__ == "__main__":
    main()
