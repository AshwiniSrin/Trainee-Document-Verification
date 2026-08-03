import json
import urllib.request

url = "http://127.0.0.1:5000/verify"
payload = {
    "name": "Jane Doe",
    "id": "123456",
    "documents": ["id_card"],
    "use_fake_data": True,
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(req, timeout=30) as response:
    print(response.read().decode("utf-8"))
