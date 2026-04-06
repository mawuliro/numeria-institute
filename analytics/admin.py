# analytics/admin.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

class AnalyticsAdmin(admin.AdminSite):
    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        app_list.append({
            'name': 'Analytics',
            'app_label': 'analytics',
            'models': [{
                'name': 'Tableau de bord',
                'object_name': 'Dashboard',
                'admin_url': reverse('analytics:dashboard'),
                'view_only': True,
            }]
        })
        return app_list

# Register your models here.
