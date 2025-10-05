import json
import requests

def publish_event(event: dict):
    url = "http://localhost:8000/api/v1/incidents/"
    response = requests.post(url, json=event)
    if response.status_code == 201:
        print(f"✅ Event published successfully: {response.json()}")
    else:
        print(f"❌ Failed to publish event: {response.status_code}, {response.text}")
    return response.status_code == 201

def publish_events(events: list[dict]):
    for event in events:
        publish_event(event)
    print(f"Published {len(events)} events.")

if __name__ == "__main__":
    with open("parsed_posts.json", "r", encoding="utf-8") as f:
        events = json.load(f)
    publish_events(events)