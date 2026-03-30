"""Zoocasa expcloud extraction preserves gallery order (not width-sorted)."""

from video_pipeline.listing_photos import extract_expcloud_photo_urls_from_html


def test_expcloud_preserves_document_order_not_width_order():
    html = """
    <html><body>
    <script>var x = "https://images.expcloud.com/aaa/1?w=150&amp;h=50";</script>
    <img src="https://images.expcloud.com/bbb/2?w=1200" />
    <img src="https://images.expcloud.com/ccc/3?w=200" />
    </body></html>
    """
    urls = extract_expcloud_photo_urls_from_html(html, max_urls=15)
    assert len(urls) == 3
    assert "/aaa/1" in urls[0]
    assert "/bbb/2" in urls[1]
    assert "/ccc/3" in urls[2]


def test_same_base_keeps_highest_w_preserves_first_seen_order_vs_other_bases():
    html = """
    https://images.expcloud.com/z/same?w=100
    https://images.expcloud.com/other/x?w=900
    https://images.expcloud.com/z/same?w=800
    """
    urls = extract_expcloud_photo_urls_from_html(html, max_urls=15)
    assert len(urls) == 2
    assert "w=800" in urls[0]
    assert "/other/x" in urls[1]


if __name__ == "__main__":
    test_expcloud_preserves_document_order_not_width_order()
    test_same_base_keeps_highest_w_preserves_first_seen_order_vs_other_bases()
    print("test_listing_photos_order: OK")
