import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}

def download_image(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.content
    except:
        pass
    return None
