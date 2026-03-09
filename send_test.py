import requests
import re
session = requests.Session()
response = session.get("http://127.0.0.1:8001/admin-plans/")
csrf_token = session.cookies['csrftoken']
# find a plan ID
plan_id = re.search(r'<input type="hidden" name="plan_id" value="(\d+)">', response.text).group(1)
print(f"Found plan ID: {plan_id}")

post_data = {
    'action': 'update_plan',
    'plan_id': plan_id,
    'price': '999',
    'billing_cycle': 'MONTHLY',
    'category_id': '',
    'csrfmiddlewaretoken': csrf_token,
    'resource_MAX_DOCTORS': '10',
    'features': ['appointments', 'patients']
}
resp2 = session.post("http://127.0.0.1:8001/admin-plans/", data=post_data)
print(f"Response status: {resp2.status_code}")
