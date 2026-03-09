import requests

response = requests.post(
    "http://127.0.0.1:8001/admin-plans/",
    data={"action": "update_plan", "plan_id": 1, "price": 1000}
)
print("status", response.status_code)
