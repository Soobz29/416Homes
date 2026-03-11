import urllib.request
import os
import time

urls = [
    "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1600&q=80",
    "https://images.unsplash.com/photo-1600607687931-cebf0746e50e?w=1600&q=80",
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1600&q=80",
    "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=1600&q=80",
    "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=1600&q=80",
    "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=1600&q=80",
    "https://images.unsplash.com/photo-1600607688969-a5bfcd64bd28?w=1600&q=80",
    "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?w=1600&q=80",
    "https://images.unsplash.com/photo-1600585154526-990dced4ea0d?w=1600&q=80",
    "https://images.unsplash.com/photo-1600573472591-ee6b68d14c68?w=1600&q=80",
    "https://images.unsplash.com/photo-1600210491892-03b5400e2069?w=1600&q=80",
    "https://images.unsplash.com/photo-1600573472592-401b489a3cdc?w=1600&q=80",
    "https://images.unsplash.com/photo-1600607687644-aac4c15ac118?w=1600&q=80",
    "https://images.unsplash.com/photo-1600566752355-35792bedcfea?w=1600&q=80",
    "https://images.unsplash.com/photo-1593696140826-c58b021acf8b?w=1600&q=80"
]

out_dir = "video_pipeline/temp/test_direct_03/photos"
os.makedirs(out_dir, exist_ok=True)

for i, url in enumerate(urls, 1):
    path = os.path.join(out_dir, f"photo_{i}.jpg")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            with open(path, 'wb') as f:
                f.write(response.read())
        print(f"Downloaded {path}")
        time.sleep(0.5)
    except Exception as e:
        print(f"Failed {path}: {e}")
