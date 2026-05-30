import json
import logging
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .utils import staff_only, log_staff_action

logger = logging.getLogger(__name__)


@staff_only
def blog_list(request):
    from blog.models import Article

    qs = Article.objects.select_related('auteur', 'categorie').all()

    status_f = request.GET.get('status', '')
    q        = request.GET.get('q', '').strip()
    mine     = request.GET.get('mine', '')

    if status_f:
        qs = qs.filter(status=status_f)
    if mine:
        qs = qs.filter(auteur=request.user)
    if q:
        qs = qs.filter(Q(titre__icontains=q) | Q(resume__icontains=q))

    paginator = Paginator(qs, 12)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_panel/blog_list.html', {
        'page_obj':  page_obj,
        'status_f':  status_f,
        'q':         q,
        'mine':      mine,
        'statuts':   [('brouillon', 'Brouillons'), ('publie', 'Publiés'), ('archive', 'Archivés')],
    })


@staff_only
def blog_create(request):
    from blog.models import Article, Categorie
    if request.method == 'POST':
        titre = request.POST.get('titre', '').strip()
        if not titre:
            messages.error(request, 'Le titre est obligatoire.')
            return redirect('admin_panel:blog_create')
        slug = slugify(titre)
        counter = 1
        base = slug
        while Article.objects.filter(slug=slug).exists():
            slug = f'{base}-{counter}'
            counter += 1
        article = Article.objects.create(
            titre=titre, slug=slug,
            resume=request.POST.get('resume', ''),
            contenu='', auteur=request.user,
            status='brouillon',
        )
        return redirect('admin_panel:blog_edit', slug=article.slug)

    from blog.models import Categorie as C
    return render(request, 'admin_panel/blog_create.html', {
        'categories': C.objects.all(),
    })


@staff_only
def blog_edit(request, slug):
    from blog.models import Article, Categorie
    article = get_object_or_404(Article, slug=slug)
    return render(request, 'admin_panel/blog_edit.html', {
        'article':    article,
        'categories': Categorie.objects.all(),
        'statuts':    Article.STATUS_ARTICLE,
    })


@staff_only
@require_POST
def blog_save(request, slug):
    from blog.models import Article, Categorie
    article = get_object_or_404(Article, slug=slug)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    article.titre    = data.get('titre', article.titre).strip() or article.titre
    article.resume   = data.get('resume', article.resume)
    article.contenu  = data.get('contenu', article.contenu)
    article.status   = data.get('status', article.status)
    article.meta_description = data.get('meta_description', article.meta_description)
    article.tags     = data.get('tags', article.tags)

    cat_id = data.get('categorie_id')
    if cat_id:
        article.categorie_id = cat_id

    if article.status == 'publie' and not article.date_publication:
        article.date_publication = timezone.now()

    if 'image_couverture' in data:
        article.image_couverture = data['image_couverture']

    article.save()
    return JsonResponse({'ok': True, 'slug': article.slug, 'titre': article.titre})


@staff_only
@require_POST
def blog_delete(request, slug):
    from blog.models import Article
    article = get_object_or_404(Article, slug=slug)
    titre = article.titre
    article.delete()
    messages.success(request, f'Article «{titre}» supprimé.')
    return redirect('admin_panel:blog_list')


@staff_only
def blog_preview(request, slug):
    from blog.models import Article
    article = get_object_or_404(Article, slug=slug)
    return render(request, 'admin_panel/blog_preview.html', {
        'article': article,
        'is_preview': True,
    })
