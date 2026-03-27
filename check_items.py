import requests
print(len(requests.get('http://127.0.0.1:8004/personalized_feed/tech_enthusiast').json().get('data',[])))
