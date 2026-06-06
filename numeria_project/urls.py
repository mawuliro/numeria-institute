from django.urls import path, include, reverse
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.contrib.sitemaps import Sitemap
from django.views.i18n import JavaScriptCatalog
from pages import views
from cours.models import Course
from cours import views_grades
from blog.models import Article


class StaticSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return ['accueil', 'a_propos', 'contact', 'cours:catalogue', 'confidentialite', 'cgu']

    def location(self, item):
        return reverse(item)


class CoursSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Course.objects.filter(status='published')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('cours:detail', args=[obj.id])


class ArticleSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Article.objects.filter(est_publie=True)

    def lastmod(self, obj):
        return obj.date_modification  # Article model has date_modification

    def location(self, obj):
        return reverse('blog:detail', args=[obj.slug])


sitemaps = {
    'static': StaticSitemap,
    'cours': CoursSitemap,
    'blog': ArticleSitemap,
}

# Routes hors i18n : admin, sitemap, i18n switcher, robots.txt, media debug
urlpatterns = [
    path('numeria-staff-portal/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
]

# Routes traduites — le français garde /, l'anglais devient /en/
urlpatterns += i18n_patterns(
    path('analytics/', include('analytics.urls')),
    path('admissions/', include('admissions.urls')),
    path('', views.accueil, name='accueil'),
    path('a-propos/', views.a_propos, name='a_propos'),
    path('contact/', views.contact, name='contact'),
    path('confidentialite/', views.confidentialite, name='confidentialite'),
    path('cgu/', views.cgu, name='cgu'),
    path('mes-notes/', views_grades.mes_notes, name='mes_notes'),
    path('mes-notes/cours/<slug:slug>/', views_grades.mes_notes_cours, name='mes_notes_cours'),
    path('mes-notes/formation/<slug:slug>/', views_grades.mes_notes_formation, name='mes_notes_formation'),
    path('cours/', include('cours.urls')),
    path('formations/', include('formation.urls', namespace='formation')),
    path('blog/', include('blog.urls')),
    path('comptes/', include('comptes.urls')),
    path('paiements/', include('paiements.urls')),
    path('communaute/', include('communaute.urls')),
    path('mentorat/', include('mentorat.urls')),
    path('notifications/', include('notifications.urls')),
    path('visio/', include('visioconference.urls')),
    path('admin-panel/', include('admin_panel.urls')),
    path('sandbox/', include('admin_panel.urls_sandbox')),
)

if settings.DEBUG or not settings.USE_CLOUDINARY:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
