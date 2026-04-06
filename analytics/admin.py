# analytics/admin.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.contrib.admin import AdminSite

# Personnaliser l'index de l'admin
admin.site.index_title = "Administration Numeria Institute"
admin.site.site_header = "Numeria Institute"

# Ajouter un widget sur la page d'accueil de l'admin
class AnalyticsAdmin(admin.AdminSite):
    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        # Ajouter Analytics comme une section
        app_list.append({
            'name': 'Analytics',
            'app_label': 'analytics',
            'models': [{
                'name': '📊 Tableau de bord Analytics',
                'object_name': 'Dashboard',
                'admin_url': reverse('analytics:dashboard'),
                'view_only': True,
                'perms': {'add': False, 'change': False, 'delete': False, 'view': True}
            }]
        })
        return app_list

# Remplacer l'admin site par défaut
# admin_site = AnalyticsAdmin(name='myadmin')
# Mais gardons simple pour l'instant
