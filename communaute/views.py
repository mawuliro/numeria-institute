from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Categorie, Sujet, Message, Vote, ProfilUtilisateur
from .forms import CategorieForm, SujetForm, MessageForm, ProfilUtilisateurForm

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

    # Récupérer les votes de l'utilisateur actuel pour chaque message
    user_votes = {}
    if request.user.is_authenticated:
        votes = Vote.objects.filter(
            message__in=[msg.pk for msg in page_obj],
            utilisateur=request.user
        ).values('message', 'valeur')
        user_votes = {vote['message']: vote['valeur'] for vote in votes}

    # Créer une liste d'objets message avec leur vote utilisateur
    messages_with_votes = []
    for message in page_obj:
        message.user_vote = user_votes.get(message.pk, 0)
        messages_with_votes.append(message)

    contexte = {
        'sujet': sujet,
        'page_obj': messages_with_votes,
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

@staff_member_required
def creer_categorie(request):
    """Permet aux modérateurs de créer une nouvelle catégorie."""
    if request.method == 'POST':
        form = CategorieForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'La catégorie a été créée avec succès.')
            return redirect('communaute:liste_categories')
    else:
        form = CategorieForm()

    contexte = {
        'form': form,
        'titre_page': 'Créer une catégorie',
    }
    return render(request, 'communaute/creer_categorie.html', contexte)

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

@login_required
@require_POST
def voter_message(request, pk):
    """Permet de voter pour ou contre un message."""
    message = get_object_or_404(Message, pk=pk)

    # Empêcher de voter pour ses propres messages
    if message.auteur == request.user:
        return JsonResponse({'error': 'Vous ne pouvez pas voter pour votre propre message.'}, status=400)

    valeur = request.POST.get('valeur')
    if valeur not in ['1', '-1']:
        return JsonResponse({'error': 'Valeur de vote invalide.'}, status=400)

    valeur = int(valeur)

    # Vérifier si l'utilisateur a déjà voté
    vote_existant = Vote.objects.filter(message=message, utilisateur=request.user).first()

    if vote_existant:
        if vote_existant.valeur == valeur:
            # Annuler le vote si c'est le même
            vote_existant.delete()
            action = 'annule'
        else:
            # Changer le vote
            vote_existant.valeur = valeur
            vote_existant.save()
            action = 'change'
    else:
        # Créer un nouveau vote
        Vote.objects.create(message=message, utilisateur=request.user, valeur=valeur)
        action = 'nouveau'

    # Retourner le nouveau nombre de votes
    nombre_votes = message.nombre_votes

    return JsonResponse({
        'action': action,
        'nombre_votes': nombre_votes,
        'vote_utilisateur': valeur if action != 'annule' else 0
    })

@login_required
def modifier_profil(request):
    """Permet à l'utilisateur de modifier son profil."""
    try:
        profil = request.user.profil_communaute
    except ProfilUtilisateur.DoesNotExist:
        profil = ProfilUtilisateur(utilisateur=request.user)

    if request.method == 'POST':
        form = ProfilUtilisateurForm(request.POST, request.FILES, instance=profil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Votre profil a été mis à jour.')
            return redirect('communaute:profil_utilisateur', username=request.user.username)
    else:
        form = ProfilUtilisateurForm(instance=profil)

    contexte = {
        'form': form,
        'titre_page': 'Modifier mon profil',
    }
    return render(request, 'communaute/modifier_profil.html', contexte)
