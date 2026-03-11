import urllib.request
import re
import gzip
import xml.etree.ElementTree as ET

req = urllib.request.Request("https://www.realtor.ca/sitemap_properties.xml", headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        data = response.read()
        try:
            html = gzip.decompress(data).decode('utf-8')
        except:
            html = data.decode('utf-8')
        
        # We need a proper URL from the sitemap
        links = re.findall(r'<loc>(https://www.realtor.ca/real-estate/\d+/[^<]+)</loc>', html)
        for link in links[:5]:
            print(link)
except Exception as e:
    print(e)
