import requests



test = requests.get("http://192.168.8.1:8001/relay/on")
print(test.text)