import urllib.request
import xml.etree.ElementTree as ET

RSS_URL = "https://metatrends.substack.com/feed"


def fetch_rss_titles(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    response = urllib.request.urlopen(request)
    data = response.read()

    root = ET.fromstring(data)

    channel = root.find("channel")
    if channel is None:
        print("No channel found in RSS feed.")
        return

    items = channel.findall("item")

    print("\nLatest RSS Articles\n")

    for item in items[:10]:
        title = item.find("title")
        if title is not None and title.text is not None:
            print("-", title.text)


if __name__ == "__main__":
    fetch_rss_titles(RSS_URL)