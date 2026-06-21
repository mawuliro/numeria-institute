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

from .models import Course, InscriptionCours, CourseLesson, ProgressionLecon, StudentProgress


def catalogue(request):
    """
    Page catalogue — affiche tous les cours publiés.
    Filtre par catégorie (matière) et par niveau.
    """
    tous_les_cours = Course.objects.filter(status='published')

    # Filtres depuis l'URL
    matiere = request.GET.get('matiere', '')
    niveau  = request.GET.get('niveau', '')

    if matiere:
        tous_les_cours = tous_les_cours.filter(category=matiere)
    if niveau:
        tous_les_cours = tous_les_cours.filter(level=niveau)

    contexte = {
        'cours':          tous_les_cours,
        'matiere_active': matiere,
        'niveau_actif':   niveau,
        'matieres':       Course.CATEGORIES,
        'niveaux':        Course.LEVELS,
    }
    return render(request, 'cours/catalogue.html', contexte)


def detail_cours(request, cours_id):
    """Page détail d'un cours avec ses leçons et exercices."""
    # TODO: Exercice, TentativeExercice, EvaluationCours, CertificatCours removed in rebuild
    from .lesson_blocks import build_lesson_blocks, build_legacy_code_exercises

    cours  = get_object_or_404(Course, id=cours_id, status='published')
    lecons = cours.lessons.filter(is_active=True).order_by('module__order', 'order')

    est_inscrit          = False
    inscription          = None
    lecons_terminees_ids = []
    evaluation_utilisateur = None
    certificat_utilisateur = None

    if request.user.is_authenticated:
        inscription = InscriptionCours.objects.filter(
            etudiant=request.user,
            course=cours
        ).first()
        est_inscrit = inscription is not None

        if est_inscrit:
            lecons_terminees_ids = list(
                ProgressionLecon.objects.filter(
                    etudiant=request.user,
                    course_lesson__course=cours
                ).values_list('course_lesson_id', flat=True)
            )
            
            # TODO: EvaluationCours removed in rebuild — evaluation_utilisateur disabled
            evaluation_utilisateur = None

            # TODO: CertificatCours removed in rebuild — use Certificat model
            certificat_utilisateur = None

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
        from .models import MCQExercise
        exercices = MCQExercise.objects.filter(course_lesson=lecon_active, is_active=True)

        exercices_reussis_ids = list(
            StudentProgress.objects.filter(
                student=request.user,
                exercise_type='mcq',
                exercise_id__in=exercices.values_list('id', flat=True),
                is_solved=True
            ).values_list('exercise_id', flat=True)
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

    # ── Code exercises (Pyodide) and LessonBlocks ────────────────────────────
    code_exercises_data = []
    lesson_blocks_data  = []

    if lecon_active and est_inscrit:
        lesson_blocks_data = build_lesson_blocks(
            course_lesson=lecon_active, user=request.user,
        )
        if not lesson_blocks_data:
            code_exercises_data = build_legacy_code_exercises(
                course_lesson=lecon_active, user=request.user,
            )

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
    cours = get_object_or_404(Course, id=cours_id, status='published')

    if InscriptionCours.objects.filter(etudiant=request.user, course=cours).exists():
        messages.info(request, _("Tu es déjà inscrit au cours « %(titre)s » ! 📚") % {'titre': cours.title})
        return redirect('cours:detail', cours_id=cours_id)

    if cours.is_free:
        InscriptionCours.objects.create(
            etudiant=request.user,
            course=cours,
            progression=0,
            est_termine=False
        )
        try:
            from notifications.notifications import notify_user
            notify_user(
                request.user,
                title=_("Inscription confirmée"),
                message=_("Vous êtes inscrit au cours %(titre)s.") % {'titre': cours.title},
                notification_type='course',
                link=reverse('cours:detail', kwargs={'cours_id': cours.id}),
            )
        except Exception as e:
            logger.error('Course enrollment notification failed: %s', e)
        messages.success(request, _("🎉 Bienvenue dans le cours « %(titre)s » !") % {'titre': cours.title})
        return redirect('cours:detail', cours_id=cours_id)
    else:
        # Cours payant — redirection vers la page de paiement
        return redirect('paiements:page_paiement', cours_id=cours_id)


@login_required
def se_desinscrire(request, cours_id):
    """Se désinscrire d'un cours."""
    cours = get_object_or_404(Course, id=cours_id)

    inscription = InscriptionCours.objects.filter(
        etudiant=request.user, course=cours
    ).first()

    if inscription:
        ProgressionLecon.objects.filter(
            etudiant=request.user, course_lesson__course=cours
        ).delete()
        inscription.delete()
        messages.success(request, _("Tu t'es désinscrit du cours « %(titre)s » .") % {'titre': cours.title})
    else:
        messages.error(request, _("Tu n'es pas inscrit à ce cours."))

    return redirect('cours:catalogue')


@login_required
def terminer_lecon(request, lecon_id):
    """Marquer une leçon comme terminée."""
    if request.method != 'POST':
        return redirect('cours:catalogue')

    lecon = get_object_or_404(CourseLesson, id=lecon_id)
    cours = lecon.course

    inscription = InscriptionCours.objects.filter(
        etudiant=request.user, course=cours
    ).first()

    if not inscription:
        messages.error(request, _("Tu n'es pas inscrit à ce cours."))
        return redirect('cours:detail', cours_id=cours.id)

    progression_lecon, cree = ProgressionLecon.objects.get_or_create(
        etudiant=request.user, course_lesson=lecon
    )

    if cree:
        total_lecons     = cours.lessons.filter(is_active=True).count()
        lecons_terminees = ProgressionLecon.objects.filter(
            etudiant=request.user, course_lesson__course=cours
        ).count()

        if total_lecons > 0:
            nouveau_pourcentage     = int((lecons_terminees / total_lecons) * 100)
            inscription.progression = nouveau_pourcentage

            if lecons_terminees >= total_lecons:
                inscription.est_termine = True
                inscription.date_fin    = timezone.now()
                messages.success(
                    request,
                    _("🎉 Félicitations ! Tu as terminé le cours « %(titre)s » !") % {'titre': cours.title}
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
    lecon_suivante = cours.lessons.filter(
        is_active=True, order__gt=lecon.order
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

    lecon = get_object_or_404(CourseLesson, id=lecon_id)
    cours = lecon.course

    inscription = InscriptionCours.objects.filter(
        etudiant=request.user, course=cours
    ).first()

    if not inscription:
        return redirect('cours:catalogue')

    ProgressionLecon.objects.filter(
        etudiant=request.user, course_lesson=lecon
    ).delete()

    total_lecons     = cours.lessons.filter(is_active=True).count()
    lecons_terminees = ProgressionLecon.objects.filter(
        etudiant=request.user, course_lesson__course=cours
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
    # TODO: Exercice / TentativeExercice removed in rebuild.
    # This legacy QCM submission endpoint is no longer active.
    # New submissions go through submit_mcq (MCQExercise).
    if request.method != 'POST':
        return redirect('cours:catalogue')
    messages.error(request, _("Ce type d'exercice n'est plus disponible."))
    return redirect('cours:catalogue')
    
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
    if inscription.course.is_free:
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
        'cours':       inscription.course,
        'date_emission': certificat.date_emission,
    }
    return render(request, 'cours/verifier_certificat.html', contexte)


@login_required
def evaluer_cours(request, cours_id):
    """Poster une évaluation pour un cours complété."""
    # TODO: EvaluationCours removed in rebuild — course evaluation disabled.
    messages.info(request, _("L'évaluation des cours sera disponible prochainement."))
    return redirect('cours:detail', cours_id=cours_id)


@login_required
def poser_question(request, cours_id):
    """Poser une question sur un cours."""
    # TODO: QuestionFAQ removed in rebuild — course Q&A disabled.
    messages.info(request, _("La FAQ des cours sera disponible prochainement."))
    return redirect('cours:detail', cours_id=cours_id)

# ─── CODE EXERCISE (Pyodide) ──────────────────────────────────────────────────

@login_required
@require_POST
def submit_code_exercise(request, exercise_id):
    """
    Receive a Pyodide code submission (client-side evaluation).
    Awards points via ExerciseGrade on first correct solve.
    """
    from .models import CodeExercise, StudentProgress, ExerciseAttempt
    from .grades import notify_exercise_solved
    from .progress import record_submission
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

    # Use StudentProgress (replaces ExerciseGrade) + ExerciseAttempt (replaces StudentCodeSubmission)
    progress, _ = StudentProgress.objects.get_or_create(
        student=request.user,
        exercise_type='code',
        exercise_id=exercise.pk,
        defaults={'attempts': 0},
    )
    already_solved = progress.is_solved
    progress.attempts = attempt_num

    points_earned = 0
    if is_correct and not already_solved:
        progress.is_solved     = True
        progress.points_earned = exercise.points
        progress.solved_at     = tz.now()
        points_earned          = exercise.points
        notify_exercise_solved(request.user, exercise.title, exercise.points)
    progress.save()

    ExerciseAttempt.objects.create(
        student=request.user,
        exercise_type='code',
        exercise_id=exercise.pk,
        attempt_number=attempt_num,
        is_correct=is_correct,
        points_earned=points_earned,
        answer_data={
            'code': code,
            'output': output,
            'time_spent_seconds': time_spent,
        },
    )

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
    from .models import CodeExercise, StudentProgress

    exercise = get_object_or_404(CodeExercise, id=exercise_id, is_active=True)

    if exercise.max_attempts > 0:
        progress = StudentProgress.objects.filter(
            student=request.user, exercise_type='code', exercise_id=exercise.pk,
        ).first()
        attempts = progress.attempts if progress else 0
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
    from .models import MCQExercise, MCQChoice, StudentProgress, ExerciseAttempt
    from .progress import record_submission
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

    # Use StudentProgress instead of removed MCQGrade
    progress, _ = StudentProgress.objects.get_or_create(
        student=request.user,
        exercise_type='mcq',
        exercise_id=mcq.pk,
        defaults={'attempts': 0},
    )

    if progress.is_solved:
        return JsonResponse({
            'is_correct': True,
            'already_solved': True,
            'points_earned': progress.points_earned,
            'attempts_used': progress.attempts,
            'max_attempts': mcq.max_attempts,
        })

    # Check max attempts
    if mcq.max_attempts > 0 and progress.attempts >= mcq.max_attempts:
        correct_ids = list(MCQChoice.objects.filter(exercise=mcq, is_correct=True).values_list('id', flat=True))
        return JsonResponse({
            'is_correct': False,
            'already_solved': False,
            'exhausted': True,
            'attempts_used': progress.attempts,
            'max_attempts': mcq.max_attempts,
            'correct_choice_ids': correct_ids,
            'explanation': mcq.explanation,
        })

    progress.attempts += 1
    progress.save(update_fields=['attempts'])

    # Evaluate correctness
    all_correct = set(MCQChoice.objects.filter(exercise=mcq, is_correct=True).values_list('id', flat=True))
    selected_set = {c.id for c in selected_choices}

    if mcq.allow_multiple_correct:
        is_correct = (selected_set == all_correct)
    else:
        is_correct = (len(selected_set) == 1 and selected_set == all_correct)

    # Record attempt via progress helper
    record_submission(
        request.user,
        mcq,
        is_correct,
        points_earned=mcq.points if is_correct else 0,
        answer_data={
            'selected_choice_ids': selected_ids,
            'attempt_number': progress.attempts,
        },
    )

    response_data = {
        'is_correct': is_correct,
        'already_solved': False,
        'exhausted': False,
        'attempts_used': progress.attempts,
        'max_attempts': mcq.max_attempts,
        'points_earned': 0,
        'per_choice_feedback': {
            str(c.id): c.feedback for c in selected_choices if c.feedback
        },
    }

    if is_correct:
        progress.is_solved = True
        progress.points_earned = mcq.points
        progress.solved_at = tz.now()
        progress.save()
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
    elif mcq.max_attempts > 0 and progress.attempts >= mcq.max_attempts:
        # Max attempts just reached — send answers
        response_data['exhausted'] = True
        response_data['correct_choice_ids'] = list(all_correct)
        response_data['explanation'] = mcq.explanation
    else:
        # Wrong but attempts remain — optionally send explanation
        if getattr(mcq, 'show_explanation_on_wrong', False) and mcq.explanation:
            response_data['explanation'] = mcq.explanation

    return JsonResponse(response_data)


@login_required
def get_mcq_status(request, mcq_id):
    """Return current grade status for the authenticated student."""
    from .models import MCQExercise, MCQChoice, StudentProgress

    mcq      = get_object_or_404(MCQExercise, id=mcq_id, is_active=True)
    progress = StudentProgress.objects.filter(
        student=request.user, exercise_type='mcq', exercise_id=mcq.pk
    ).first()

    if not progress:
        return JsonResponse({
            'is_solved': False, 'points_earned': 0,
            'attempts_used': 0, 'correct_choice_ids': [],
        })

    correct_ids = []
    if progress.is_solved or (mcq.max_attempts > 0 and progress.attempts >= mcq.max_attempts):
        correct_ids = list(MCQChoice.objects.filter(exercise=mcq, is_correct=True).values_list('id', flat=True))

    return JsonResponse({
        'is_solved':      progress.is_solved,
        'points_earned':  progress.points_earned,
        'attempts_used':  progress.attempts,
        'correct_choice_ids': correct_ids,
        'explanation': mcq.explanation if progress.is_solved else '',
    })


# ─── 5 NEW EXERCISE TYPE SUBMISSION ENDPOINTS ────────────────────────────────
# All server-evaluated (no Pyodide). Correct answers NEVER sent to browser.

def _get_exercise_type(exercise):
    """Map exercise class to exercise_type string."""
    from .models import (
        CodeExercise, MCQExercise, FillBlankExercise, TrueFalseExercise,
        CodeOrderExercise, MatchingExercise, ShortAnswerExercise,
    )
    TYPE_MAP = {
        CodeExercise: 'code', MCQExercise: 'mcq', FillBlankExercise: 'fill_blank',
        TrueFalseExercise: 'true_false', CodeOrderExercise: 'code_order',
        MatchingExercise: 'matching', ShortAnswerExercise: 'short_answer',
    }
    return TYPE_MAP.get(type(exercise), 'code')


def _award_and_respond(request, exercise, progress, is_correct, points_max,
                       attempts_count, extra=None, answer_data=None):
    """Common response builder for all server-evaluated exercise types.
    progress is a StudentProgress instance (replaces removed XxxGrade models).
    """
    from .grades import notify_exercise_solved
    from .progress import record_submission
    from django.utils import timezone as tz

    already_solved = progress.is_solved
    progress.attempts = attempts_count

    points_earned = 0
    if is_correct and not already_solved:
        progress.is_solved     = True
        progress.points_earned = points_max
        progress.solved_at     = tz.now()
        points_earned          = points_max
        notify_exercise_solved(request.user, exercise.title, points_max)
    progress.save()

    record_submission(
        request.user, exercise, is_correct,
        points_earned=points_earned, answer_data=answer_data,
    )

    exhausted = (
        hasattr(exercise, 'max_attempts') and exercise.max_attempts > 0
        and attempts_count >= exercise.max_attempts
    )
    show_explanation = is_correct or exhausted or already_solved

    data = {
        'is_correct':    is_correct,
        'points_earned': points_earned,
        'already_solved': already_solved,
        'attempts_used': attempts_count,
        'max_attempts':  exercise.max_attempts if hasattr(exercise, 'max_attempts') else 0,
        'explanation': (
            getattr(exercise, 'explanation', '') or ''
        ) if show_explanation else '',
    }
    if extra:
        data.update(extra)
    return JsonResponse(data)


def _get_progress(user, exercise):
    """Get or create a StudentProgress record for the given exercise."""
    from .models import StudentProgress
    ex_type = _get_exercise_type(exercise)
    progress, _ = StudentProgress.objects.get_or_create(
        student=user,
        exercise_type=ex_type,
        exercise_id=exercise.pk,
        defaults={'attempts': 0},
    )
    return progress


@login_required
@require_POST
def submit_fill_blank(request, exercise_id):
    from .models import FillBlankExercise
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

    progress = _get_progress(request.user, ex)
    progress.attempts = (progress.attempts or 0) + 1
    return _award_and_respond(
        request, ex, progress, all_correct, ex.points,
        progress.attempts, extra={'blank_results': results}
    )


@login_required
@require_POST
def submit_true_false(request, exercise_id):
    from .models import TrueFalseExercise
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

    progress = _get_progress(request.user, ex)
    progress.attempts = (progress.attempts or 0) + 1
    return _award_and_respond(
        request, ex, progress, is_correct, points_max,
        progress.attempts,
        extra={'feedback': feedback, 'points_partial': points_earned_partial}
    )


@login_required
@require_POST
def submit_code_order(request, exercise_id):
    from .models import CodeOrderExercise
    ex = get_object_or_404(CodeOrderExercise, id=exercise_id, is_active=True)
    try:
        submitted_order = json.loads(request.body).get('submitted_order', [])
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    correct = list(range(len(ex.correct_order)))   # indices 0..n-1
    is_correct = (list(submitted_order) == correct)

    progress = _get_progress(request.user, ex)
    progress.attempts = (progress.attempts or 0) + 1
    extra = {}
    if is_correct:
        extra['correct_code'] = '\n'.join(ex.correct_order)
    return _award_and_respond(request, ex, progress, is_correct, ex.points, progress.attempts, extra=extra)


@login_required
@require_POST
def submit_matching(request, exercise_id):
    from .models import MatchingExercise
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

    total          = len(pairs)
    is_correct     = (correct_count == total)
    points_max     = ex.points
    points_partial = round(ex.points * correct_count / total) if total else 0

    progress = _get_progress(request.user, ex)
    progress.attempts = (progress.attempts or 0) + 1
    return _award_and_respond(
        request, ex, progress, is_correct, points_max, progress.attempts,
        extra={'correct_count': correct_count, 'total': total, 'points_partial': points_partial}
    )


@login_required
@require_POST
def submit_short_answer(request, exercise_id):
    from .models import ShortAnswerExercise
    ex = get_object_or_404(ShortAnswerExercise, id=exercise_id, is_active=True)
    try:
        answer = json.loads(request.body).get('answer', '')
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if getattr(ex, 'strip_whitespace', True):
        answer = answer.strip()
    accepted = [a.strip() for a in (ex.accepted_answers or [])]
    if not ex.case_sensitive:
        answer   = answer.lower()
        accepted = [a.lower() for a in accepted]

    is_correct = answer in accepted

    progress = _get_progress(request.user, ex)
    progress.attempts = (progress.attempts or 0) + 1
    extra = {}
    if is_correct and ex.explanation:
        extra['explanation'] = ex.explanation
    return _award_and_respond(request, ex, progress, is_correct, ex.points, progress.attempts, extra=extra)
