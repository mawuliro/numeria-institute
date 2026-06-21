from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import F
from .models import Article, Categorie


def liste_articles(request):
    """
    Vue pour la page liste du blog.
    Affiche tous les articles publiés, avec pagination.
    """

    articles_list = Article.objects.filter(
        est_publie=True
    ).select_related('auteur', 'categorie').order_by('-date_creation')

    paginator = Paginator(articles_list, 20)
    page_number = request.GET.get('page')
    articles = paginator.get_page(page_number)

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

    article = get_object_or_404(
        Article.objects.select_related('auteur', 'categorie'),
        slug=slug,
        est_publie=True,
    )

    Article.objects.filter(pk=article.pk).update(nombre_vues=F('nombre_vues') + 1)

    # 3 articles récents pour la sidebar
    articles_recents = Article.objects.filter(
        est_publie=True
    ).exclude(id=article.id).select_related('auteur', 'categorie').order_by('-date_creation')[:3]

    contexte = {
        'article': article,
        'articles_recents': articles_recents,
    }

    return render(request, 'blog/detail.html', contexte)