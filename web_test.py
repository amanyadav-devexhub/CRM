import requests

s = requests.Session()
r = s.get("http://127.0.0.1:8001/admin-plans/")
token = s.cookies['csrftoken']
import re
# Get all html
html = r.text
plan_match = re.search(r'<input type="hidden" name="plan_id" value="(\d+)">', html)
plan_id = plan_match.group(1)
print("Plan ID:", plan_id)

data = {
    'csrfmiddlewaretoken': token,
    'action': 'update_plan',
    'plan_id': plan_id,
    'display_name': 'Clinic Free UPDATE',
    'price': '0',
    'billing_cycle': 'MONTHLY',
    'category_id': '',
    'resource_MAX_DOCTORS': '10',
    'features': ['appointments', 'patients']
}
r2 = s.post("http://127.0.0.1:8001/admin-plans/", data=data)
print("status:", r2.status_code)
# check if display name updated
r3 = s.get("http://127.0.0.1:8001/admin-plans/")
if "Clinic Free UPDATE" in r3.text:
    print("Update successful!")
else:
    print("Update failed!")

