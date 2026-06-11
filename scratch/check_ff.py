import requests
import cloudscraper

url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
try:
    scraper = cloudscraper.create_scraper()
    response = scraper.get(url, timeout=15)
    print("Status:", response.status_code)
    print("Headers:", response.headers)
    print("Content preview:", response.text[:200])
    data = response.json()
    print("Total events:", len(data))
except Exception as e:
    print("Error:", e)
