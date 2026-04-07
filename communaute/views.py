from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from .models import Categorie, Sujet, Message, ProfilUtilisateur
from .forms import SujetForm, MessageForm, ProfilUtilisateurForm

def liste_categories(request):
    """Affiche la liste des catégories de forums."""
    categories = Categorie.objects.filter(est_active=True).annotate(
        nombre_sujets=Count('sujets'),
        dernier_message=Count('sujets__messages')
    ).order_by('ordre')

    contexte = {
        'categories': categories,
        'titre_page': 'Communauté',
    }
    return render(request, 'communaute/liste_categories.html', contexte)

def detail_categorie(request, pk):
    """Affiche les détails d'une catégorie et ses sujets."""
    categorie = get_object_or_404(Categorie, pk=pk, est_active=True)
    sujets = categorie.sujets.all().order_by('-est_epingle', '-date_modification')

    # Pagination
    paginator = Paginator(sujets, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    contexte = {
        'categorie': categorie,
        'page_obj': page_obj,
        'titre_page': f'Forum - {categorie.nom}',
    }
    return render(request, 'communaute/detail_categorie.html', contexte)

def detail_sujet(request, pk):
    """Affiche les détails d'un sujet et ses messages."""
    sujet = get_object_or_404(Sujet, pk=pk)

    # Incrémenter le compteur de vues
    sujet.vues += 1
    sujet.save(update_fields=['vues'])

    messages_sujet = sujet.messages.all().order_by('date_creation')

    # Pagination des messages
    paginator = Paginator(messages_sujet, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    contexte = {
        'sujet': sujet,
        'page_obj': page_obj,
        'titre_page': sujet.titre,
    }
    return render(request, 'communaute/detail_sujet.html', contexte)

@login_required
def creer_sujet(request):
    """Permet de créer un nouveau sujet."""
    categorie_initial = request.GET.get('categorie')
    if request.method == 'POST':
        form = SujetForm(request.POST)
        if form.is_valid():
            sujet = form.save(commit=False)
            sujet.auteur = request.user
            sujet.save()

            # Créer le premier message
            Message.objects.create(
                sujet=sujet,
                auteur=request.user,
                contenu=form.cleaned_data['contenu']
            )

            messages.success(request, 'Votre sujet a été créé avec succès.')
            return redirect(sujet.get_absolute_url())
    else:
        form_kwargs = {}
        if categorie_initial:
            form_kwargs['categorie_initial'] = categorie_initial
        form = SujetForm(**form_kwargs)

    contexte = {
        'form': form,
        'titre_page': 'Créer un nouveau sujet',
    }
    return render(request, 'communaute/creer_sujet.html', contexte)

@login_required
def repondre_sujet(request, pk):
    """Permet de répondre à un sujet."""
    sujet = get_object_or_404(Sujet, pk=pk)

    if sujet.est_ferme:
        messages.error(request, 'Ce sujet est fermé.')
        return redirect(sujet.get_absolute_url())

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sujet = sujet
            message.auteur = request.user
            message.save()

            messages.success(request, 'Votre réponse a été publiée.')
            return redirect(message.get_absolute_url())
    else:
        form = MessageForm()

    contexte = {
        'form': form,
        'sujet': sujet,
        'titre_page': f'Répondre à : {sujet.titre}',
    }
    return render(request, 'communaute/repondre_sujet.html', contexte)

@login_required
def modifier_sujet(request, pk):
    """Permet de modifier un sujet (seulement l'auteur)."""
    sujet = get_object_or_404(Sujet, pk=pk)

    if sujet.auteur != request.user:
        messages.error(request, 'Vous ne pouvez pas modifier ce sujet.')
        return redirect(sujet.get_absolute_url())

    if request.method == 'POST':
        form = SujetForm(request.POST, instance=sujet)
        if form.is_valid():
            form.save()
            messages.success(request, 'Le sujet a été modifié.')
            return redirect(sujet.get_absolute_url())
    else:
        # Pré-remplir avec le contenu du premier message
        premier_message = sujet.messages.first()
        initial_data = {
            'titre': sujet.titre,
            'categorie': sujet.categorie,
            'contenu': premier_message.contenu if premier_message else '',
        }
        form = SujetForm(instance=sujet, initial=initial_data)

    contexte = {
        'form': form,
        'sujet': sujet,
        'titre_page': f'Modifier : {sujet.titre}',
    }
    return render(request, 'communaute/modifier_sujet.html', contexte)

@login_required
def modifier_message(request, pk):
    """Permet de modifier un message (seulement l'auteur)."""
    message = get_object_or_404(Message, pk=pk)

    if message.auteur != request.user:
        messages.error(request, 'Vous ne pouvez pas modifier ce message.')
        return redirect(message.get_absolute_url())

    if request.method == 'POST':
        form = MessageForm(request.POST, instance=message)
        if form.is_valid():
            message = form.save(commit=False)
            message.est_edite = True
            message.save()
            messages.success(request, 'Le message a été modifié.')
            return redirect(message.get_absolute_url())
    else:
        form = MessageForm(instance=message)

    contexte = {
        'form': form,
        'message': message,
        'titre_page': 'Modifier le message',
    }
    return render(request, 'communaute/modifier_message.html', contexte)

def profil_utilisateur(request, username):
    """Affiche le profil d'un utilisateur."""
    from django.contrib.auth.models import User
    utilisateur = get_object_or_404(User, username=username)

    try:
        profil = utilisateur.profil_communaute
    except ProfilUtilisateur.DoesNotExist:
        profil = None

    # Statistiques
    nombre_sujets = utilisateur.sujets.count()
    nombre_messages = utilisateur.messages.count()
    derniers_messages = utilisateur.messages.order_by('-date_creation')[:5]

    contexte = {
        'utilisateur': utilisateur,
        'profil': profil,
        'nombre_sujets': nombre_sujets,
        'nombre_messages': nombre_messages,
        'derniers_messages': derniers_messages,
        'titre_page': f'Profil de {utilisateur.username}',
    }
    return render(request, 'communaute/profil_utilisateur.html', contexte)
