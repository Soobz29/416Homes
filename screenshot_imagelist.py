from scraper.browser_util import create_browser
import time

url = "https://www.realtor.ca/real-estate/29457635/512-142-dundas-street-east-toronto-moss-park-toronto-moss-park-m?view=imagelist"

page = create_browser(headless=False)
page.get(url, retry=2, interval=2, timeout=25)
time.sleep(8)
page.get_screenshot(path="debug_realtor_imagelist_live.png", full_page=True)
print("Screenshot saved to debug_realtor_imagelist_live.png")
with open("debug_realtor_imagelist_live.html", "w", encoding="utf-8") as f:
    f.write(page.html)
page.quit()
