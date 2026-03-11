import urllib.request
import re
import gzip
import xml.etree.ElementTree as ET

req = urllib.request.Request("https://www.realtor.ca/sitemap_properties.xml", headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        # Realtor.ca sitemaps are often gzipped, let's just try to read it
        data = response.read()
        try:
            html = gzip.decompress(data).decode('utf-8')
        except:
            html = data.decode('utf-8')
        
        links = re.findall(r'https://www.realtor.ca/real-estate/\d+/[^\s<]+', html)
        found = False
        for link in links:
            if 'toronto' in link.lower():
                print(link)
                found = True
                break
        if not found and links:
            print("No toronto link found, using any:")
            print(links[0])
            
except Exception as e:
    print(e)
