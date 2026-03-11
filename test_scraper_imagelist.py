import time
import sys
from DrissionPage import ChromiumPage

def scrape_live_listing():
    page = ChromiumPage()
    
    # 1. Go to Realtor.ca map search for Toronto directly
    toronto_map_url = "https://www.realtor.ca/map#ZoomLevel=12&Center=43.682828%2C-79.388836&LatitudeMin=43.61529&LongitudeMin=-79.50763&LatitudeMax=43.75027&LongitudeMax=-79.27005&Sort=6-D&PGeoIds=g30_dpz89rm7&GeoName=Toronto%2C%20ON&PropertyTypeGroupID=1&TransactionTypeId=2&PropertySearchTypeId=1&Currency=CAD&HiddenListingIds=&IncludeHiddenListings=false"
    print(f"Navigating to map: {toronto_map_url[:50]}...")
    page.get(toronto_map_url)
    time.sleep(5)
    
    # 2. Find first listing card Link
    try:
        cards = page.eles('.listingCard')
        if not cards:
            cards = page.eles('tag:a@@href:realtor.ca/real-estate/')
            
        links = []
        for card in page.eles('tag:a'):
            href = card.attr('href')
            if href and '/real-estate/' in href:
                links.append(href)
                
        if not links:
            print("No listing links found on map!")
            page.quit()
            return
            
        target_url = links[0]
        if not target_url.startswith('http'):
            target_url = "https://www.realtor.ca" + target_url
            
        print(f"Found live listing: {target_url}")
        
    except Exception as e:
        print(f"Error finding card: {e}")
        page.quit()
        return

    # 3. Append ?view=imagelist
    if '?' in target_url:
        img_url = target_url + "&view=imagelist"
    else:
        img_url = target_url + "?view=imagelist"
        
    print(f"Loading imagelist view: {img_url}")
    page.get(img_url)
    time.sleep(5)
    
    # 4. Save debug
    page.get_screenshot(path="realtor_live_debug.png", full_page=True)
    
    # 5. Extract images
    all_imgs = page.eles('tag:img')
    saved = []
    for img in all_imgs:
        src = img.attr('src') or ''
        # Filter for properties
        if src.startswith('http') and ('picture' in src.lower() or 'photo' in src.lower() or 'listing' in src. lower() or 'property' in src.lower() or '/cdn' in src.lower()):
            if width := img.attr('width'):
                if int(width) < 100: continue
            saved.append(src)
            print(f"IMG: {src}")
            
    print(f"Total Property Photos: {len(saved)}")
    page.quit()

if __name__ == "__main__":
    scrape_live_listing()
