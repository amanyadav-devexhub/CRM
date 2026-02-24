import os
import glob
import re

nav_content = """{% block hub_nav %}
<div class="nav-section">
    <div class="nav-section-title">Enterprise Layer</div>
    <a href="{% url 'category-hospitals' %}" class="nav-item {% if request.resolver_match.url_name == 'category-hospitals' %}active{% endif %}">
        <span class="icon material-icons-round">dashboard</span>
        Executive Dashboard
    </a>
    <a href="{% url 'hospital-departments' %}" class="nav-item {% if request.resolver_match.url_name == 'hospital-departments' %}active{% endif %}">
        <span class="icon material-icons-round">account_balance</span>
        Departments
    </a>
    <a href="{% url 'hospital-wards' %}" class="nav-item {% if request.resolver_match.url_name == 'hospital-wards' %}active{% endif %}">
        <span class="icon material-icons-round">domain</span>
        Ward Management
    </a>
    <a href="{% url 'hospital-beds' %}" class="nav-item {% if request.resolver_match.url_name == 'hospital-beds' %}active{% endif %}">
        <span class="icon material-icons-round">bed</span>
        Bed Management
    </a>
    <a href="{% url 'hospital-staffing' %}" class="nav-item {% if request.resolver_match.url_name == 'hospital-staffing' %}active{% endif %}">
        <span class="icon material-icons-round">groups</span>
        Staffing Control
    </a>
    <a href="{% url 'hospital-insurance' %}" class="nav-item {% if request.resolver_match.url_name == 'hospital-insurance' %}active{% endif %}">
        <span class="icon material-icons-round">receipt_long</span>
        Revenue Cycle
    </a>
</div>
<div class="nav-section">
    <div class="nav-section-title">Operations</div>
    <a href="{% url 'hospital-er-console' %}" class="nav-item {% if request.resolver_match.url_name == 'hospital-er-console' %}active{% endif %}">
        <span class="icon material-icons-round">emergency</span>
        ER Board
    </a>
    <a href="{% url 'hospital-admissions' %}" class="nav-item {% if request.resolver_match.url_name == 'hospital-admissions' or request.resolver_match.url_name == 'patient-monitoring' %}active{% endif %}">
        <span class="icon material-icons-round">login</span>
        IPD Admissions
    </a>
    <a href="{% url 'hospital-patients' %}" class="nav-item {% if 'patient' in request.resolver_match.url_name and request.resolver_match.url_name != 'patient-monitoring' %}active{% endif %}">
        <span class="icon material-icons-round">personal_injury</span>
        Patients
    </a>
</div>
<div class="nav-section">
    <div class="nav-section-title">Standalone Panels</div>
    <a href="{% url 'category-clinic' %}" class="nav-item">
        <span class="icon material-icons-round">stethoscope</span>
        Clinic Panel
    </a>
    <a href="/categories/labs/" class="nav-item">
        <span class="icon material-icons-round">biotech</span>
        Laboratory
    </a>
    <a href="{% url 'category-pharmacy' %}" class="nav-item">
        <span class="icon material-icons-round">local_pharmacy</span>
        Pharmacy
    </a>
</div>
{% endblock %}"""

def update_file(filepath):
    if "invoice" in filepath: return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "{% block hub_nav %}" in content:
        content = re.sub(r'\{% block hub_nav %\}.*?\{% endblock %\}', nav_content, content, flags=re.DOTALL)
        content = re.sub(r'\{% block hub_name %\}.*?\{% endblock %\}', '{% block hub_name %}Enterprise Control{% endblock %}', content, flags=re.DOTALL)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

files = glob.glob('c:/Users/Simran/Downloads/CRM/templates/categories/hospital_*.html')
for f in files:
    update_file(f)
print(f"Updated files")
