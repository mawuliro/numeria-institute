from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.http import HttpResponse
import uuid
from numeria_project.emails import send_course_enrollment_email
from .models import Cours, InscriptionCours, Lecon, ProgressionLecon


def catalogue(request):
    """
    Page catalogue — affiche tous les cours publiés.
    Filtre par type (général ou scolaire), par cycle et par classe.
    """
    tous_les_cours = Cours.objects.filter(est_publie=True)

    # Filtres depuis l'URL
    type_cours = request.GET.get('type', '')
    cycle      = request.GET.get('cycle', '')
    classe     = request.GET.get('classe', '')
    matiere    = request.GET.get('matiere', '')

    if type_cours:
        tous_les_cours = tous_les_cours.filter(type_cours=type_cours)
    if cycle:
        tous_les_cours = tous_les_cours.filter(cycle=cycle)
    if classe:
        tous_les_cours = tous_les_cours.filter(classe=classe)
    if matiere:
        tous_les_cours = tous_les_cours.filter(matiere=matiere)

    # Compteurs par type
    cours_generaux  = Cours.objects.filter(est_publie=True, type_cours='general').count()
    cours_scolaires = Cours.objects.filter(est_publie=True, type_cours='scolaire').count()

    contexte = {
        'cours':           tous_les_cours,
        'cours_generaux':  cours_generaux,
        'cours_scolaires': cours_scolaires,
        'type_actif':      type_cours,
        'cycle_actif':     cycle,
        'classe_active':   classe,
        'matiere_active':  matiere,
        'cycles':          Cours.CYCLES,
        'classes':         Cours.CLASSES,
        'matieres':        Cours.MATIERES,
    }
    return render(request, 'cours/catalogue.html', contexte)


def detail_cours(request, cours_id):
    """Page détail d'un cours avec ses leçons et exercices."""
    from .models import Exercice, TentativeExercice, EvaluationCours, CertificatCours

    cours  = get_object_or_404(Cours, id=cours_id, est_publie=True)
    lecons = cours.lecons.filter(est_publiee=True)

    est_inscrit          = False
    inscription          = None
    lecons_terminees_ids = []
    evaluation_utilisateur = None
    certificat_utilisateur = None

    if request.user.is_authenticated:
        inscription = InscriptionCours.objects.filter(
            etudiant=request.user,
            cours=cours
        ).first()
        est_inscrit = inscription is not None

        if est_inscrit:
            lecons_terminees_ids = list(
                ProgressionLecon.objects.filter(
                    etudiant=request.user,
                    lecon__cours=cours
                ).values_list('lecon_id', flat=True)
            )
            
            # Get user's evaluation if exists
            evaluation_utilisateur = EvaluationCours.objects.filter(
                etudiant=request.user,
                cours=cours
            ).first()
            
            # Get user's certificate if the course is completed
            if inscription.est_termine:
                certificat_utilisateur = CertificatCours.objects.filter(
                    etudiant=request.user,
                    cours=cours,
                    statut__in=['gagne', 'en_cours']
                ).first()

    # Leçon active
    lecon_active_id = request.GET.get('lecon')
    lecon_active    = None
    if lecon_active_id and est_inscrit:
        lecon_active = lecons.filter(id=lecon_active_id).first()
    if not lecon_active and lecons.exists():
        lecon_active = lecons.first()

    # Leçon précédente et suivante
    lecon_precedente = None
    lecon_suivante   = None
    if lecon_active:
        lecons_list = list(lecons)
        idx = next((i for i, l in enumerate(lecons_list) if l.id == lecon_active.id), None)
        if idx is not None:
            if idx > 0:
                lecon_precedente = lecons_list[idx - 1]
            if idx < len(lecons_list) - 1:
                lecon_suivante = lecons_list[idx + 1]

    # Exercices de la leçon active
    exercices              = []
    exercices_reussis_ids  = []
    resultat_exercice      = None
    exercice_actif_id      = None
    reponse_choisie        = None

    if lecon_active and est_inscrit:
        exercices = lecon_active.exercices.filter(est_actif=True)

        exercices_reussis_ids = list(
            TentativeExercice.objects.filter(
                etudiant=request.user,
                exercice__lecon=lecon_active,
                est_correcte=True
            ).values_list('exercice_id', flat=True)
        )

        resultat_exercice = request.GET.get('resultat')
        exercice_actif_id = request.GET.get('exercice')
        reponse_choisie   = request.GET.get('choisie', '').upper()

        if exercice_actif_id:
            try:
                exercice_actif_id = int(exercice_actif_id)
            except (ValueError, TypeError):
                exercice_actif_id = None

    total_lecons           = lecons.count()
    lecons_terminees_count = len(lecons_terminees_ids)

    contexte = {
        'cours':                  cours,
        'lecons':                 lecons,
        'lecon_active':           lecon_active,
        'lecon_precedente':       lecon_precedente,
        'lecon_suivante':         lecon_suivante,
        'est_inscrit':            est_inscrit,
        'inscription':            inscription,
        'lecons_terminees_ids':   lecons_terminees_ids,
        'total_lecons':           total_lecons,
        'lecons_terminees_count': lecons_terminees_count,
        'exercices':              exercices,
        'exercices_reussis_ids':  exercices_reussis_ids,
        'resultat_exercice':      resultat_exercice,
        'exercice_actif_id':      exercice_actif_id,
        'reponse_choisie':        reponse_choisie,
        'evaluation_utilisateur': evaluation_utilisateur,
        'certificat_utilisateur': certificat_utilisateur,
    }
    return render(request, 'cours/detail.html', contexte)


@login_required
def inscrire_cours(request, cours_id):
    """S'inscrire à un cours — gratuit ou payant."""
    cours = get_object_or_404(Cours, id=cours_id, est_publie=True)

    if InscriptionCours.objects.filter(etudiant=request.user, cours=cours).exists():
        messages.info(request, _("Tu es déjà inscrit au cours « %(titre)s » ! 📚") % {'titre': cours.titre})
        return redirect('cours:detail', cours_id=cours_id)

    if cours.est_gratuit:
        InscriptionCours.objects.create(
            etudiant=request.user,
            cours=cours,
            progression=0,
            est_termine=False
        )
        send_course_enrollment_email(request.user, cours, language=getattr(request, 'LANGUAGE_CODE', None))
        messages.success(request, _("🎉 Bienvenue dans le cours « %(titre)s » !") % {'titre': cours.titre})
        return redirect('cours:detail', cours_id=cours_id)
    else:
        # Cours payant — redirection vers la page de paiement
        return redirect('paiements:page_paiement', cours_id=cours_id)


@login_required
def se_desinscrire(request, cours_id):
    """Se désinscrire d'un cours."""
    cours = get_object_or_404(Cours, id=cours_id)

    inscription = InscriptionCours.objects.filter(
        etudiant=request.user, cours=cours
    ).first()

    if inscription:
        ProgressionLecon.objects.filter(
            etudiant=request.user, lecon__cours=cours
        ).delete()
        inscription.delete()
        messages.success(request, _("Tu t'es désinscrit du cours « %(titre)s » .") % {'titre': cours.titre})
    else:
        messages.error(request, _("Tu n'es pas inscrit à ce cours."))

    return redirect('cours:catalogue')


@login_required
def terminer_lecon(request, lecon_id):
    """Marquer une leçon comme terminée."""
    if request.method != 'POST':
        return redirect('cours:catalogue')

    lecon = get_object_or_404(Lecon, id=lecon_id)
    cours = lecon.cours

    inscription = InscriptionCours.objects.filter(
        etudiant=request.user, cours=cours
    ).first()

    if not inscription:
        messages.error(request, _("Tu n'es pas inscrit à ce cours."))
        return redirect('cours:detail', cours_id=cours.id)

    progression_lecon, cree = ProgressionLecon.objects.get_or_create(
        etudiant=request.user, lecon=lecon
    )

    if cree:
        total_lecons     = cours.lecons.filter(est_publiee=True).count()
        lecons_terminees = ProgressionLecon.objects.filter(
            etudiant=request.user, lecon__cours=cours
        ).count()

        if total_lecons > 0:
            nouveau_pourcentage     = int((lecons_terminees / total_lecons) * 100)
            inscription.progression = nouveau_pourcentage

            if lecons_terminees >= total_lecons:
                inscription.est_termine = True
                inscription.date_fin    = timezone.now()
                messages.success(
                    request,
                    _("🎉 Félicitations ! Tu as terminé le cours « %(titre)s » !") % {'titre': cours.titre}
                )
            else:
                messages.success(
                    request,
                    _("✅ Leçon terminée ! Progression : %(pct)s%%") % {'pct': nouveau_pourcentage}
                )
            inscription.save()
    else:
        messages.info(request, _("Cette leçon était déjà marquée comme terminée."))

    # Rediriger vers la leçon suivante si elle existe
    lecon_suivante = cours.lecons.filter(
        est_publiee=True, ordre__gt=lecon.ordre
    ).first()

    url_detail = reverse('cours:detail', kwargs={'cours_id': cours.id})
    if lecon_suivante:
        return redirect(f'{url_detail}?lecon={lecon_suivante.id}')
    return redirect(url_detail)


@login_required
def annuler_lecon(request, lecon_id):
    """Annuler la complétion d'une leçon."""
    if request.method != 'POST':
        return redirect('cours:catalogue')

    lecon = get_object_or_404(Lecon, id=lecon_id)
    cours = lecon.cours

    inscription = InscriptionCours.objects.filter(
        etudiant=request.user, cours=cours
    ).first()

    if not inscription:
        return redirect('cours:catalogue')

    ProgressionLecon.objects.filter(
        etudiant=request.user, lecon=lecon
    ).delete()

    total_lecons     = cours.lecons.filter(est_publiee=True).count()
    lecons_terminees = ProgressionLecon.objects.filter(
        etudiant=request.user, lecon__cours=cours
    ).count()

    if total_lecons > 0:
        inscription.progression = int((lecons_terminees / total_lecons) * 100)
        inscription.est_termine = False
        inscription.date_fin    = None
        inscription.save()

    messages.info(request, _("Leçon marquée comme non terminée."))
    return redirect('cours:detail', cours_id=cours.id)


@login_required
def soumettre_exercice(request, exercice_id):
    """
    Traite la soumission d'une réponse à un exercice QCM.
    Vérifie si la réponse est correcte côté serveur.
    Le corrigé n'est JAMAIS envoyé si la réponse est fausse.
    """
    from .models import Exercice, TentativeExercice

    if request.method != 'POST':
        return redirect('cours:catalogue')

    exercice = get_object_or_404(Exercice, id=exercice_id, est_actif=True)
    lecon    = exercice.lecon
    cours    = lecon.cours

    # Vérifier que l'étudiant est inscrit
    if not InscriptionCours.objects.filter(
        etudiant=request.user,
        cours=cours
    ).exists():
        messages.error(request, _("Tu n'es pas inscrit à ce cours."))
        return redirect('cours:detail', cours_id=cours.id)

    # Récupérer la réponse choisie
    reponse_choisie = request.POST.get('reponse', '').upper()

    if reponse_choisie not in ['A', 'B', 'C', 'D']:
        messages.error(request, _("Réponse invalide."))
        # CORRIGÉ : reverse() au lieu de syntaxe template dans du Python
        url_detail = reverse('cours:detail', kwargs={'cours_id': cours.id})
        return redirect(f'{url_detail}?lecon={lecon.id}')

    # Compter les tentatives précédentes
    nb_tentatives = TentativeExercice.objects.filter(
        etudiant=request.user,
        exercice=exercice
    ).count()

    # Vérifier si la réponse est correcte
    est_correcte = (reponse_choisie == exercice.bonne_reponse)

    # Enregistrer la tentative
    TentativeExercice.objects.create(
        etudiant=request.user,
        exercice=exercice,
        reponse_choisie=reponse_choisie,
        est_correcte=est_correcte,
        numero_tentative=nb_tentatives + 1
    )

    # Rediriger vers la leçon avec le résultat dans l'URL
    url_detail = reverse('cours:detail', kwargs={'cours_id': cours.id})
    if est_correcte:
        return redirect(
            f'{url_detail}?lecon={lecon.id}&exercice={exercice_id}&resultat=correct'
        )
    else:
        return redirect(
            f'{url_detail}?lecon={lecon.id}&exercice={exercice_id}'
            f'&resultat=incorrect&choisie={reponse_choisie}'
        )
    
@login_required
def telecharger_certificat(request, inscription_id):
    """
    Génère et télécharge le certificat PDF d'un cours terminé.
    Réservé aux cours payants uniquement.
    """
    from .models import Certificat
    from .utils.certificat import generer_certificat_pdf

    inscription = get_object_or_404(
        InscriptionCours,
        id=inscription_id,
        etudiant=request.user,
        est_termine=True
    )

    # Vérifier que le cours est payant
    if inscription.cours.est_gratuit:
        messages.error(
            request,
            _("Les certificats sont réservés aux cours payants.")
        )
        return redirect('comptes:tableau_de_bord')

    # Récupérer ou créer le certificat
    certificat, cree = Certificat.objects.get_or_create(
        inscription=inscription,
        defaults={
            'code_verification': uuid.uuid4().hex
        }
    )

    # Construire l'URL de vérification
    url_verification = request.build_absolute_uri(
        reverse('cours:verifier_certificat',
                kwargs={'code': certificat.code_verification})
    )

    # Générer le PDF
    pdf = generer_certificat_pdf(inscription, url_verification)

    # Retourner le PDF en téléchargement
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="{certificat.get_nom_fichier()}"'
    )
    return response


def verifier_certificat(request, code):
    """
    Page publique de vérification d'un certificat via le QR code.
    Accessible sans connexion.
    """
    from .models import Certificat

    certificat = get_object_or_404(Certificat, code_verification=code)
    inscription = certificat.inscription

    contexte = {
        'certificat':  certificat,
        'inscription': inscription,
        'etudiant':    inscription.etudiant,
        'cours':       inscription.cours,
        'date_emission': certificat.date_emission,
    }
    return render(request, 'cours/verifier_certificat.html', contexte)


@login_required
def evaluer_cours(request, cours_id):
    """Poster une évaluation pour un cours complété."""
    from .models import EvaluationCours
    
    cours = get_object_or_404(Cours, id=cours_id, est_publie=True)
    inscription = InscriptionCours.objects.filter(
        etudiant=request.user,
        cours=cours,
        est_termine=True
    ).first()
    
    if not inscription:
        messages.error(request, _("Vous devez terminer le cours avant de le noter."))
        return redirect('cours:detail', cours_id=cours_id)
    
    if request.method == 'POST':
        try:
            note = int(request.POST.get('note', 0) or 0)
            if note < 1 or note > 5:
                messages.error(request, _("La note doit être entre 1 et 5."))
                return redirect('cours:detail', cours_id=cours_id)
            
            commentaire = request.POST.get('commentaire', '').strip()
            
            # Créer ou mettre à jour l'évaluation
            evaluation, created = EvaluationCours.objects.update_or_create(
                etudiant=request.user,
                cours=cours,
                defaults={
                    'note': note,
                    'commentaire': commentaire,
                }
            )
            
            messages.success(request, _("✅ Merci pour votre évaluation !"))
        except Exception as e:
            messages.error(request, _("Erreur lors de l'évaluation : %(err)s") % {'err': str(e)})
        
        return redirect('cours:detail', cours_id=cours_id)
    
    return redirect('cours:detail', cours_id=cours_id)


@login_required
def poser_question(request, cours_id):
    """Poser une question sur un cours."""
    from .models import QuestionFAQ
    
    cours = get_object_or_404(Cours, id=cours_id, est_publie=True)
    inscription = InscriptionCours.objects.filter(
        etudiant=request.user,
        cours=cours
    ).first()
    
    if not inscription:
        messages.error(request, _("Vous devez être inscrit au cours pour poser une question."))
        return redirect('cours:detail', cours_id=cours_id)
    
    if request.method == 'POST':
        try:
            question = request.POST.get('question', '').strip()
            if not question or len(question) < 5:
                messages.error(request, _("La question doit contenir au moins 5 caractères."))
                return redirect('cours:detail', cours_id=cours_id)
            if len(question) > 500:
                messages.error(request, _("La question ne peut pas dépasser 500 caractères."))
                return redirect('cours:detail', cours_id=cours_id)
            
            # Créer la question (en attente de modération)
            QuestionFAQ.objects.create(
                cours=cours,
                auteur=request.user,
                question=question,
                reponse="",  # Will be filled by admin
                approuvee_par_admin=False
            )
            
            messages.success(request, _("✅ Votre question a été soumise et sera modérée par un admin."))
        except Exception as e:
            messages.error(request, _("Erreur lors de la soumission : %(err)s") % {'err': str(e)})
        
        return redirect('cours:detail', cours_id=cours_id)
    
    return redirect('cours:detail', cours_id=cours_id)