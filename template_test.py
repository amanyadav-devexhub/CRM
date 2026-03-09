import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.template import Template, Context

t = Template("""
<input type="checkbox" name="features" value="{{ f.code }}" {{ f.is_assigned|yesno:"checked," }}>
""")
c1 = Context({'f': {'code': 'abc', 'is_assigned': True}})
c2 = Context({'f': {'code': 'abc', 'is_assigned': False}})
print("True rendered:", t.render(c1).strip())
print("False rendered:", t.render(c2).strip())
