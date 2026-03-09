import requests
import re
session = requests.Session()
response = session.get("http://127.0.0.1:8001/admin-plans/")
csrf_token = session.cookies.get('csrftoken', 'nocookies')
match = re.search(r'<input type="hidden" name="plan_id" value="(\d+)">', response.text)
if not match:
    print("Could not find a plan ID")
    exit(1)
plan_id = match.group(1)
print(f"Found plan ID: {plan_id}")

post_data = {
    'action': 'update_plan',
    'plan_id': plan_id,
    'price': '999',
    'display_name': 'Test Plan Updated',
    'billing_cycle': 'MONTHLY',
    'category_id': '',
    'csrfmiddlewaretoken': re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text).group(1),
    'resource_MAX_DOCTORS': '10',
    'features': ['appointments', 'patients']
}
resp2 = session.post("http://127.0.0.1:8001/admin-plans/", data=post_data)
print(f"Response status: {resp2.status_code}")
