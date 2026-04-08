from django.urls import path, include, reverse
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.contrib.sitemaps import Sitemap
from pages import views
from cours.models import Cours
from blog.models import Article


class StaticSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return ['accueil', 'a_propos', 'contact', 'cours:catalogue']

    def location(self, item):
        return reverse(item)


class CoursSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Cours.objects.filter(est_publie=True)

    def lastmod(self, obj):
        return obj.date_modification


class ArticleSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Article.objects.filter(est_publie=True)

    def lastmod(self, obj):
        return obj.date_modification


sitemaps = {
    'static': StaticSitemap,
    'cours': CoursSitemap,
    'blog': ArticleSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('analytics/', include('analytics.urls')),
    path('admissions/', include('admissions.urls')),
    path('', views.accueil, name='accueil'),
    path('a-propos/', views.a_propos, name='a_propos'),
    path('contact/', views.contact, name='contact'),
    path('cours/', include('cours.urls')),
    path('blog/', include('blog.urls')),
    path('comptes/', include('comptes.urls')),
    path('paiements/', include('paiements.urls')),
    path('communaute/', include('communaute.urls')),
    path('mentorat/', include('mentorat.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)