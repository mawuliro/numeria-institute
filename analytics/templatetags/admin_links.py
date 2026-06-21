# analytics/templatetags/admin_links.py
from django import template
from django.urls import reverse

register = template.Library()

@register.simple_tag
def admin_analytics_link():
    return reverse('analytics:dashboard')