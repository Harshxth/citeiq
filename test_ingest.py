import requests
import base64

with open("data/test.txt", "rb") as f:
    content_b64 = base64.b64encode(f.read()).decode("utf-8")

response = requests.post(
    "http://localhost:8000/ingest",
    json={"filename": "test.txt", "content_b64": content_b64}
)
print(response.status_code)
print(response.text)