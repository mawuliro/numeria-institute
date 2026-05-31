import base64
import json
import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
import uuid

logger = logging.getLogger(__name__)

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

    # ── Code exercises (Pyodide) ───────────────────────────────────────────
    code_exercises_data = []
    lesson_blocks_data  = []   # populated when lesson has LessonBlocks

    if lecon_active and est_inscrit:
        from .models import CodeExercise, StudentCodeSubmission, LessonBlock

        # ── LessonBlocks (new system) ─────────────────────────────────────
        blocks_qs = LessonBlock.objects.filter(lesson=lecon_active).order_by('order')
        if blocks_qs.exists():
            solved_ids = set(
                StudentCodeSubmission.objects.filter(
                    student=request.user,
                    exercise__lesson_blocks__lesson=lecon_active,
                    is_correct=True,
                ).values_list('exercise_id', flat=True)
            )
            for block in blocks_qs:
                bd = {
                    'id':         block.id,
                    'type':       block.block_type,
                    'order':      block.order,
                }
                if block.block_type == 'text':
                    bd['text_content'] = block.text_content
                elif block.block_type == 'video':
                    bd['video_url']    = block.video_url
                    bd['video_caption']= block.video_caption
                    if block.video_url:
                        from .models import convertir_url_youtube
                        bd['embed_url'] = convertir_url_youtube(block.video_url)
                elif block.block_type == 'sandbox':
                    bd['title']        = block.sandbox_title or 'Essaie toi-même'
                    bd['initial_code'] = block.sandbox_initial_code
                elif block.block_type == 'exercise' and block.exercise:
                    ex    = block.exercise
                    tc_b64 = base64.b64encode(ex.test_code.encode()).decode() if ex.test_code else ''
                    bd.update({
                        'exercise_id':    ex.id,
                        'title':          ex.title,
                        'instructions':   ex.instructions,
                        'starter_code':   ex.starter_code,
                        'expected_output':ex.expected_output,
                        'evaluation_mode':ex.evaluation_mode,
                        'difficulty':     ex.difficulty,
                        'hint':           ex.hint,
                        'max_attempts':   ex.max_attempts,
                        'points':         ex.points,
                        'test_code_b64':  tc_b64,
                        'is_solved':      ex.id in solved_ids,
                        # solution_code intentionally omitted
                    })
                elif block.block_type == 'mcq' and block.mcq_exercise:
                    from .models import MCQExercise, MCQGrade, MCQChoice
                    mcq   = block.mcq_exercise
                    grade = MCQGrade.objects.filter(student=request.user, exercise=mcq).first()
                    choices = list(mcq.choices.order_by('order'))
                    exhausted = (grade and mcq.max_attempts > 0 and
                                 grade.attempts_count >= mcq.max_attempts)
                    reveal = (grade and (grade.is_solved or exhausted))
                    bd.update({
                        'mcq_id':        mcq.id,
                        'mcq_title':     mcq.title,
                        'question':      mcq.question,
                        'hint':          mcq.hint,
                        'allow_multiple':mcq.allow_multiple_correct,
                        'shuffle':       mcq.shuffle_choices,
                        'max_attempts':  mcq.max_attempts,
                        'points':        mcq.points,
                        'difficulty':    mcq.difficulty,
                        'choices':       [{'id': c.id, 'text': c.text, 'order': c.order} for c in choices],
                        'is_solved':     grade.is_solved if grade else False,
                        'points_earned': grade.points_earned if grade else 0,
                        'attempts_used': grade.attempts_count if grade else 0,
                        # Only send correct IDs when solved or exhausted
                        'correct_ids':   [c.id for c in choices if c.is_correct] if reveal else [],
                        'explanation':   mcq.explanation if reveal else '',
                    })

                # ── FillBlank block ───────────────────────────────────────
                elif block.block_type == 'fill_blank' and block.fill_blank_exercise:
                    from .models import FillBlankExercise, FillBlankGrade
                    ex = block.fill_blank_exercise
                    gr = FillBlankGrade.objects.filter(student=request.user, exercise=ex).first()
                    bd.update({
                        'fill_blank_id': ex.id, 'title': ex.title,
                        'instructions': ex.instructions,
                        'text_rendered': ex.text_with_blanks,
                        'blank_count': len(ex.answers or {}),
                        'points': ex.points, 'difficulty': ex.difficulty,
                        'hint': ex.hint, 'max_attempts': ex.max_attempts,
                        'is_solved': gr.is_solved if gr else False,
                        'attempts_used': gr.attempts_count if gr else 0,
                    })

                # ── TrueFalse block ───────────────────────────────────────
                elif block.block_type == 'true_false' and block.true_false_exercise:
                    from .models import TrueFalseExercise, TrueFalseGrade
                    ex = block.true_false_exercise
                    gr = TrueFalseGrade.objects.filter(student=request.user, exercise=ex).first()
                    stmts = [{'statement': s.get('statement',''), 'is_true': s.get('is_true', True)} for s in (ex.statements or [])]
                    bd.update({
                        'true_false_id': ex.id, 'title': ex.title,
                        'statements': stmts,
                        'points_per_statement': ex.points_per_statement,
                        'difficulty': ex.difficulty, 'hint': ex.hint,
                        'is_solved': gr.is_solved if gr else False,
                        'attempts_used': gr.attempts_count if gr else 0,
                    })

                # ── CodeOrder block ───────────────────────────────────────
                elif block.block_type == 'code_order' and block.code_order_exercise:
                    from .models import CodeOrderExercise, CodeOrderGrade
                    import random as _random
                    ex = block.code_order_exercise
                    gr = CodeOrderGrade.objects.filter(student=request.user, exercise=ex).first()
                    all_lines = list(ex.correct_order) + list(ex.distractor_lines or [])
                    indices = list(range(len(all_lines)))
                    _random.seed(request.user.id + ex.id)
                    _random.shuffle(indices)
                    shuffled = [all_lines[i] for i in indices]
                    import json as _json
                    bd.update({
                        'code_order_id': ex.id, 'title': ex.title,
                        'instructions': ex.instructions,
                        'shuffled_lines': shuffled,
                        'shuffled_indices_json': _json.dumps(indices),
                        'points': ex.points, 'difficulty': ex.difficulty,
                        'hint': ex.hint, 'max_attempts': ex.max_attempts,
                        'is_solved': gr.is_solved if gr else False,
                        'attempts_used': gr.attempts_count if gr else 0,
                    })

                # ── Matching block ────────────────────────────────────────
                elif block.block_type == 'matching' and block.matching_exercise:
                    from .models import MatchingExercise, MatchingGrade
                    import random as _random
                    ex = block.matching_exercise
                    gr = MatchingGrade.objects.filter(student=request.user, exercise=ex).first()
                    pairs = ex.pairs or []
                    left = [p.get('left','') for p in pairs]
                    right = [p.get('right','') for p in pairs]
                    indices = list(range(len(right)))
                    _random.seed(request.user.id + ex.id + 1)
                    _random.shuffle(indices)
                    shuffled_right = [right[i] for i in indices]
                    bd.update({
                        'matching_id': ex.id, 'title': ex.title,
                        'instructions': ex.instructions,
                        'left_items': left, 'right_items': shuffled_right,
                        'right_indices': list(range(len(pairs))),
                        'pairs': pairs,
                        'points': ex.points, 'difficulty': ex.difficulty,
                        'hint': ex.hint,
                        'is_solved': gr.is_solved if gr else False,
                        'attempts_used': gr.attempts_count if gr else 0,
                    })

                # ── ShortAnswer block ─────────────────────────────────────
                elif block.block_type == 'short_answer' and block.short_answer_exercise:
                    from .models import ShortAnswerExercise, ShortAnswerGrade
                    ex = block.short_answer_exercise
                    gr = ShortAnswerGrade.objects.filter(student=request.user, exercise=ex).first()
                    bd.update({
                        'short_answer_id': ex.id, 'title': ex.title,
                        'question': ex.question,
                        'points': ex.points, 'difficulty': ex.difficulty,
                        'hint': ex.hint, 'max_attempts': ex.max_attempts,
                        'is_code_answer': ex.is_code_answer,
                        'is_solved': gr.is_solved if gr else False,
                        'attempts_used': gr.attempts_count if gr else 0,
                        # accepted_answers intentionally omitted for security
                    })

                lesson_blocks_data.append(bd)

        else:
            # ── Legacy: CodeExercise only (no blocks yet) ─────────────────
            raw_exs = CodeExercise.objects.filter(
                lecon=lecon_active, is_active=True
            ).order_by('order')
            solved_ids = set(
                StudentCodeSubmission.objects.filter(
                    student=request.user,
                    exercise__lecon=lecon_active,
                    is_correct=True,
                ).values_list('exercise_id', flat=True)
            )
            for ex in raw_exs:
                tc_b64 = base64.b64encode(ex.test_code.encode()).decode() if ex.test_code else ''
                code_exercises_data.append({
                    'id':               ex.id,
                    'title':            ex.title,
                    'instructions':     ex.instructions,
                    'starter_code':     ex.starter_code,
                    'expected_output':  ex.expected_output,
                    'evaluation_mode':  ex.evaluation_mode,
                    'difficulty':       ex.difficulty,
                    'hint':             ex.hint,
                    'max_attempts':     ex.max_attempts,
                    'points':           ex.points,
                    'order':            ex.order,
                    'test_code_b64':    tc_b64,
                    'is_solved':        ex.id in solved_ids,
                })

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
        'lesson_blocks':          lesson_blocks_data,
        'code_exercises':         code_exercises_data,
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
        try:
            from notifications.notifications import notify_user
            notify_user(
                request.user,
                title=_("Inscription confirmée"),
                message=_("Vous êtes inscrit au cours %(titre)s.") % {'titre': cours.titre},
                notification_type='course',
                link=reverse('cours:detail', kwargs={'cours_id': cours.id}),
            )
        except Exception as e:
            logger.error('Course enrollment notification failed: %s', e)
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

# ─── CODE EXERCISE (Pyodide) ──────────────────────────────────────────────────

@login_required
@require_POST
def submit_code_exercise(request, exercise_id):
    """
    Receive a Pyodide code submission (client-side evaluation).
    Awards points via ExerciseGrade on first correct solve.
    """
    from .models import CodeExercise, StudentCodeSubmission, ExerciseGrade
    from .grades import notify_exercise_solved
    from django.utils import timezone as tz

    exercise = get_object_or_404(CodeExercise, id=exercise_id, is_active=True)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    code        = body.get('code', '')
    output      = body.get('output', '')
    is_correct  = bool(body.get('is_correct', False))
    attempt_num = int(body.get('attempt_number', 1))
    time_spent  = int(body.get('time_spent', 0))

    StudentCodeSubmission.objects.create(
        student=request.user,
        exercise=exercise,
        code_submitted=code,
        output_received=output,
        is_correct=is_correct,
        attempt_number=attempt_num,
        time_spent_seconds=time_spent,
    )

    grade, _ = ExerciseGrade.objects.get_or_create(
        student=request.user, exercise=exercise
    )
    grade.attempts_count = attempt_num
    grade.time_spent_seconds = (grade.time_spent_seconds or 0) + time_spent

    points_earned = 0
    already_solved = grade.is_solved

    if is_correct and not already_solved:
        grade.is_solved     = True
        grade.points_earned = exercise.points
        grade.solved_at     = tz.now()
        points_earned       = exercise.points
        notify_exercise_solved(request.user, exercise.title, exercise.points)
    grade.save()

    return JsonResponse({
        'success': True,
        'points_earned': points_earned,
        'total_points': points_earned,
        'is_correct': is_correct,
        'already_solved': already_solved,
        'attempts_used': attempt_num,
        'max_attempts': exercise.max_attempts,
    })


@login_required
def get_exercise_solution(request, exercise_id):
    """Return solution code only when the student has exhausted attempts."""
    from .models import CodeExercise, StudentCodeSubmission

    exercise = get_object_or_404(CodeExercise, id=exercise_id, is_active=True)

    if exercise.max_attempts > 0:
        attempts = StudentCodeSubmission.objects.filter(
            student=request.user, exercise=exercise
        ).count()
        if attempts < exercise.max_attempts:
            return JsonResponse({'error': 'Attempts not exhausted'}, status=403)

    return JsonResponse({'solution': exercise.solution_code})


# ─── MCQ EXERCISES ────────────────────────────────────────────────────────────

@login_required
@require_POST
def submit_mcq(request, mcq_id):
    """
    Receive a student's MCQ answer.
    Never sends correct_choice_ids or explanation before solved/max attempts.
    """
    from .models import MCQExercise, MCQChoice, MCQSubmission, MCQGrade
    from django.utils import timezone as tz

    mcq = get_object_or_404(MCQExercise, id=mcq_id, is_active=True)

    try:
        body = json.loads(request.body)
        selected_ids = [int(x) for x in body.get('selected_choice_ids', [])]
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Security: verify all selected choices belong to this exercise
    selected_choices = list(MCQChoice.objects.filter(id__in=selected_ids, exercise=mcq))
    if len(selected_choices) != len(selected_ids):
        return JsonResponse({'error': 'Invalid choice IDs'}, status=400)

    # Get or create grade record
    grade, _ = MCQGrade.objects.get_or_create(
        student=request.user, exercise=mcq
    )

    if grade.is_solved:
        return JsonResponse({
            'is_correct': True,
            'already_solved': True,
            'points_earned': grade.points_earned,
            'attempts_used': grade.attempts_count,
            'max_attempts': mcq.max_attempts,
        })

    # Check max attempts
    if mcq.max_attempts > 0 and grade.attempts_count >= mcq.max_attempts:
        correct_ids = list(MCQChoice.objects.filter(exercise=mcq, is_correct=True).values_list('id', flat=True))
        return JsonResponse({
            'is_correct': False,
            'already_solved': False,
            'exhausted': True,
            'attempts_used': grade.attempts_count,
            'max_attempts': mcq.max_attempts,
            'correct_choice_ids': correct_ids,
            'explanation': mcq.explanation,
        })

    grade.attempts_count += 1
    grade.save(update_fields=['attempts_count'])

    # Evaluate correctness
    all_correct = set(MCQChoice.objects.filter(exercise=mcq, is_correct=True).values_list('id', flat=True))
    selected_set = {c.id for c in selected_choices}

    if mcq.allow_multiple_correct:
        is_correct = (selected_set == all_correct)
    else:
        is_correct = (len(selected_set) == 1 and selected_set == all_correct)

    # Save submission
    sub = MCQSubmission.objects.create(
        student=request.user, exercise=mcq,
        is_correct=is_correct,
        attempt_number=grade.attempts_count,
        points_earned=mcq.points if is_correct else 0,
    )
    sub.selected_choices.set(selected_choices)

    response_data = {
        'is_correct': is_correct,
        'already_solved': False,
        'exhausted': False,
        'attempts_used': grade.attempts_count,
        'max_attempts': mcq.max_attempts,
        'points_earned': 0,
        'per_choice_feedback': {
            str(c.id): c.feedback for c in selected_choices if c.feedback
        },
    }

    if is_correct:
        grade.is_solved = True
        grade.points_earned = mcq.points
        grade.solved_at = tz.now()
        grade.save()
        response_data['points_earned'] = mcq.points
        response_data['explanation'] = mcq.explanation
        # Notify
        try:
            from notifications.notifications import notify_user
            notify_user(
                request.user,
                title=_("QCM réussi ! 🎉"),
                message=_("Tu as répondu correctement à '%(title)s' (+%(pts)s pts)") % {
                    'title': mcq.title, 'pts': mcq.points
                },
                notification_type='success',
            )
        except Exception:
            pass
    elif mcq.max_attempts > 0 and grade.attempts_count >= mcq.max_attempts:
        # Max attempts just reached — send answers
        response_data['exhausted'] = True
        response_data['correct_choice_ids'] = list(all_correct)
        response_data['explanation'] = mcq.explanation
    else:
        # Wrong but attempts remain — optionally send explanation
        if mcq.show_explanation_on_wrong and mcq.explanation:
            response_data['explanation'] = mcq.explanation

    return JsonResponse(response_data)


@login_required
def get_mcq_status(request, mcq_id):
    """Return current grade status for the authenticated student."""
    from .models import MCQExercise, MCQChoice, MCQGrade

    mcq   = get_object_or_404(MCQExercise, id=mcq_id, is_active=True)
    grade = MCQGrade.objects.filter(student=request.user, exercise=mcq).first()

    if not grade:
        return JsonResponse({
            'is_solved': False, 'points_earned': 0,
            'attempts_used': 0, 'correct_choice_ids': [],
        })

    correct_ids = []
    if grade.is_solved or (mcq.max_attempts > 0 and grade.attempts_count >= mcq.max_attempts):
        correct_ids = list(MCQChoice.objects.filter(exercise=mcq, is_correct=True).values_list('id', flat=True))

    return JsonResponse({
        'is_solved':      grade.is_solved,
        'points_earned':  grade.points_earned,
        'attempts_used':  grade.attempts_count,
        'correct_choice_ids': correct_ids,
        'explanation': mcq.explanation if grade.is_solved else '',
    })


# ─── 5 NEW EXERCISE TYPE SUBMISSION ENDPOINTS ────────────────────────────────
# All server-evaluated (no Pyodide). Correct answers NEVER sent to browser.

def _award_and_respond(request, exercise, grade, is_correct, points_max,
                       attempts_count, extra=None):
    """Common response builder for all server-evaluated exercise types."""
    from .grades import notify_exercise_solved
    from django.utils import timezone as tz

    already_solved = grade.is_solved
    grade.attempts_count = attempts_count

    points_earned = 0
    if is_correct and not already_solved:
        grade.is_solved     = True
        grade.points_earned = points_max
        grade.solved_at     = tz.now()
        points_earned       = points_max
        notify_exercise_solved(request.user, exercise.title, points_max)
    grade.save()

    data = {
        'is_correct':    is_correct,
        'points_earned': points_earned,
        'already_solved':already_solved,
        'attempts_used': attempts_count,
        'max_attempts':  exercise.max_attempts if hasattr(exercise, 'max_attempts') else 0,
    }
    if extra:
        data.update(extra)
    return JsonResponse(data)


@login_required
@require_POST
def submit_fill_blank(request, exercise_id):
    from .models import FillBlankExercise, FillBlankGrade
    ex = get_object_or_404(FillBlankExercise, id=exercise_id, is_active=True)
    try:
        submitted = json.loads(request.body).get('answers', {})
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    correct_answers = ex.answers or {}
    results = {}
    all_correct = True
    for key, accepted in correct_answers.items():
        student_ans = submitted.get(key, '').strip()
        if not ex.case_sensitive:
            student_ans = student_ans.lower()
            accepted = [a.strip().lower() for a in accepted]
        else:
            accepted = [a.strip() for a in accepted]
        ok = student_ans in accepted
        results[key] = ok
        if not ok:
            all_correct = False

    grade, _ = FillBlankGrade.objects.get_or_create(student=request.user, exercise=ex)
    grade.attempts_count = (grade.attempts_count or 0) + 1
    return _award_and_respond(
        request, ex, grade, all_correct, ex.points,
        grade.attempts_count, extra={'blank_results': results}
    )


@login_required
@require_POST
def submit_true_false(request, exercise_id):
    from .models import TrueFalseExercise, TrueFalseGrade
    ex = get_object_or_404(TrueFalseExercise, id=exercise_id, is_active=True)
    try:
        submitted = json.loads(request.body).get('answers', [])
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    statements = ex.statements or []
    correct_count = 0
    feedback = []
    for i, stmt in enumerate(statements):
        student = submitted[i] if i < len(submitted) else None
        correct = stmt.get('is_true', False)
        ok = (student == correct)
        if ok:
            correct_count += 1
        feedback.append({'ok': ok, 'explanation': stmt.get('explanation', '')})

    points_max   = ex.points_per_statement * len(statements)
    points_earned_partial = ex.points_per_statement * correct_count
    is_correct   = (correct_count == len(statements))

    grade, _ = TrueFalseGrade.objects.get_or_create(student=request.user, exercise=ex)
    grade.attempts_count = (grade.attempts_count or 0) + 1
    return _award_and_respond(
        request, ex, grade, is_correct, points_max,
        grade.attempts_count,
        extra={'feedback': feedback, 'points_partial': points_earned_partial}
    )


@login_required
@require_POST
def submit_code_order(request, exercise_id):
    from .models import CodeOrderExercise, CodeOrderGrade
    ex = get_object_or_404(CodeOrderExercise, id=exercise_id, is_active=True)
    try:
        submitted_order = json.loads(request.body).get('submitted_order', [])
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    correct = list(range(len(ex.correct_order)))   # indices 0..n-1
    is_correct = (list(submitted_order) == correct)

    grade, _ = CodeOrderGrade.objects.get_or_create(student=request.user, exercise=ex)
    grade.attempts_count = (grade.attempts_count or 0) + 1
    extra = {}
    if is_correct:
        extra['correct_code'] = '\n'.join(ex.correct_order)
    return _award_and_respond(request, ex, grade, is_correct, ex.points, grade.attempts_count, extra=extra)


@login_required
@require_POST
def submit_matching(request, exercise_id):
    from .models import MatchingExercise, MatchingGrade
    ex = get_object_or_404(MatchingExercise, id=exercise_id, is_active=True)
    try:
        submitted_pairs = json.loads(request.body).get('pairs', [])
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    pairs = ex.pairs or []
    # submitted_pairs: [{"left_index": 0, "right_index": 2}, ...]
    correct_count = 0
    for sp in submitted_pairs:
        li = sp.get('left_index')
        ri = sp.get('right_index')
        if li is not None and ri is not None and 0 <= li < len(pairs):
            # Correct pair: li matches li (right[li] belongs to left[li])
            if li == ri:
                correct_count += 1

    total        = len(pairs)
    is_correct   = (correct_count == total)
    points_max   = ex.points
    points_partial = round(ex.points * correct_count / total) if total else 0

    grade, _ = MatchingGrade.objects.get_or_create(student=request.user, exercise=ex)
    grade.attempts_count = (grade.attempts_count or 0) + 1
    return _award_and_respond(
        request, ex, grade, is_correct, points_max, grade.attempts_count,
        extra={'correct_count': correct_count, 'total': total, 'points_partial': points_partial}
    )


@login_required
@require_POST
def submit_short_answer(request, exercise_id):
    from .models import ShortAnswerExercise, ShortAnswerGrade
    ex = get_object_or_404(ShortAnswerExercise, id=exercise_id, is_active=True)
    try:
        answer = json.loads(request.body).get('answer', '')
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if ex.strip_whitespace:
        answer = answer.strip()
    accepted = [a.strip() for a in (ex.accepted_answers or [])]
    if not ex.case_sensitive:
        answer   = answer.lower()
        accepted = [a.lower() for a in accepted]

    is_correct = answer in accepted

    grade, _ = ShortAnswerGrade.objects.get_or_create(student=request.user, exercise=ex)
    grade.attempts_count = (grade.attempts_count or 0) + 1
    extra = {}
    if is_correct and ex.explanation:
        extra['explanation'] = ex.explanation
    return _award_and_respond(request, ex, grade, is_correct, ex.points, grade.attempts_count, extra=extra)
