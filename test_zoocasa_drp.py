from DrissionPage import ChromiumPage, ChromiumOptions
import time
import json

def main():
    co = ChromiumOptions()
    co.headless(False)
    co.set_browser_path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    
    page = ChromiumPage(co)
    
    # Listen for ALL network traffic to find listing data
    page.listen.start('search.zoocasa.com')
    
    target_url = "https://www.zoocasa.com/toronto-on-real-estate"
    print(f"Navigating to {target_url}...")
    page.get(target_url, retry=1, interval=1, timeout=20)
    
    print("Waiting 15s for all API calls...")
    time.sleep(15)
    
    # Dump ALL intercepted responses to find where listing data lives
    packets = []
    for packet in page.listen.steps():
        if packet and packet.response:
            packets.append(packet)
    
    print(f"\nIntercepted {len(packets)} API calls:")
    
    for i, pkt in enumerate(packets):
        print(f"\n--- Packet {i+1}: {pkt.url[:120]} ---")
        print(f"  Status: {pkt.response.status}")
        try:
            body = pkt.response.body
            if isinstance(body, str):
                # Try to parse as JSON
                try:
                    body = json.loads(body)
                except:
                    print(f"  Body (text, first 200 chars): {body[:200]}")
                    continue
                    
            if isinstance(body, dict):
                print(f"  Dict keys: {list(body.keys())[:20]}")
                # Recursively dump all keys that contain lists
                for k, v in body.items():
                    if isinstance(v, list) and len(v) > 0:
                        print(f"  '{k}' is a list of {len(v)} items")
                        if isinstance(v[0], dict):
                            print(f"    First item keys: {list(v[0].keys())[:20]}")
                            # Print first item preview
                            preview = {kk: vv for kk, vv in list(v[0].items())[:8]}
                            print(f"    First item preview: {json.dumps(preview, default=str)[:300]}")
                    elif isinstance(v, dict):
                        for k2, v2 in v.items():
                            if isinstance(v2, list) and len(v2) > 0:
                                print(f"  '{k}'.'{k2}' is a list of {len(v2)} items")
                                if isinstance(v2[0], dict):
                                    print(f"    First item keys: {list(v2[0].keys())[:20]}")
                                    preview = {kk: vv for kk, vv in list(v2[0].items())[:8]}
                                    print(f"    First item preview: {json.dumps(preview, default=str)[:300]}")
            elif isinstance(body, list):
                print(f"  Response is a list of {len(body)} items")
                if body and isinstance(body[0], dict):
                    print(f"  First item keys: {list(body[0].keys())[:20]}")
        except Exception as e:
            print(f"  Error reading body: {e}")
    
    page.quit()

if __name__ == "__main__":
    main()
