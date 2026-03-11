import json
from bs4 import BeautifulSoup

def main():
    with open("zoocasa_debug.html", "r", encoding="utf-8") as f:
        html = f.read()
        
    soup = BeautifulSoup(html, 'html.parser')
    script = soup.find('script', id='__NEXT_DATA__')
    
    if script:
        data = json.loads(script.string)
        
        # Traverse recursively to find objects with prices or addresses
        found_properties = []
        
        def find_objects(d):
            if isinstance(d, dict):
                # A property object usually has an address, price, and bathrooms/bedrooms
                has_price = 'price' in d or 'listPrice' in d or 'ListPrice' in d
                has_address = 'address' in d or 'streetName' in d or 'Address' in d
                
                if has_price and has_address:
                    found_properties.append(d)
                else:
                    for v in d.values():
                        find_objects(v)
            elif isinstance(d, list):
                for item in d:
                    find_objects(item)
                    
        find_objects(data)
        
        print(f"Found {len(found_properties)} potential property objects")
        if found_properties:
            print("Keys of first object:", found_properties[0].keys())
            for idx, prop in enumerate(found_properties[:5]):
                price = prop.get('price') or prop.get('listPrice') or prop.get('ListPrice') or 'NoPrice'
                address = prop.get('address') or prop.get('streetName') or prop.get('Address') or 'NoAddress'
                print(f"{idx+1}. {address} - {price}")

if __name__ == "__main__":
    main()
