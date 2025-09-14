import requests

def test_brave_search(api_key):
    headers = {"X-Subscription-Token": api_key}
    response = requests.get(
        "https://api.search.brave.com/res/v1/web/search?q=test",
        headers=headers
    )
    
    if response.status_code == 200:
        print("✅ API key works!")
        print(f"Found {len(response.json()['web']['results'])} results")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

test_brave_search("YOUR-API-KEY")