from django.shortcuts import render, get_object_or_404
from .models import Article, Categorie


def liste_articles(request):
    """
    Vue pour la page liste du blog.
    Affiche tous les articles publiés.
    """

    # Tous les articles publiés
    articles = Article.objects.filter(est_publie=True)

    # Toutes les catégories — pour le filtre sur la page
    categories = Categorie.objects.all()

    contexte = {
        'articles': articles,
        'categories': categories,
    }

    return render(request, 'blog/liste.html', contexte)


def detail_article(request, slug):
    """
    Vue pour la page détail d'un article.
    On utilise le slug au lieu de l'id pour une belle URL.
    Ex: /blog/introduction-algebre-lineaire/
    """

    # On cherche l'article par son slug
    # Si introuvable → page 404 automatiquement
    article = get_object_or_404(Article, slug=slug, est_publie=True)

    # On incrémente le nombre de vues à chaque visite
    article.nombre_vues += 1
    article.save()

    # 3 articles récents pour la sidebar
    articles_recents = Article.objects.filter(
        est_publie=True
    ).exclude(id=article.id)[:3]
    # exclude(id=article.id) → on exclut l'article actuel

    contexte = {
        'article': article,
        'articles_recents': articles_recents,
    }

    return render(request, 'blog/detail.html', contexte)