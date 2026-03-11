import urllib.request
import re

url = "https://html.duckduckgo.com/html/?q=site:realtor.ca/real-estate/+toronto"
req = urllib.request.Request(
    url, 
    data=None, 
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'
    }
)

try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        links = re.findall(r'href="(https://www\.realtor\.ca/real-estate/[^"]+)"', html)
        if links:
            print(f"Found {len(links)} links. First 3:")
            for l in links[:3]:
                print(l)
        else:
            print("No links found.")
            # dump a bit of html
            print(html[:500])
except Exception as e:
    print(f"Error: {e}")
