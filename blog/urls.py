from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    # Liste des articles : /blog/
    path('', views.liste_articles, name='liste'),

    # Détail d'un article : /blog/introduction-algebre-lineaire/
    # <slug:slug> capture le slug dans l'URL
    path('<slug:slug>/', views.detail_article, name='detail'),
]