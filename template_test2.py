import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.template import Template, Context

t = Template("""
<input type="checkbox" name="features" value="{{ f.code }}" {{ f.checked_str }} style="...">
""")
c1 = Context({'f': {'code': 'abc', 'checked_str': 'checked'}})
c2 = Context({'f': {'code': 'abc', 'checked_str': ''}})
print("True:", t.render(c1).strip())
print("False:", t.render(c2).strip())
