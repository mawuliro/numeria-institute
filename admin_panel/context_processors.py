def staff_counts(request):
    """Inject sidebar badge counts only for staff users on admin-panel paths."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return {}
    path = request.path
    is_admin_path = (
        '/admin-panel/' in path
        or path.endswith('/admin-panel/')
    )
    if not is_admin_path:
        return {}
    try:
        from pages.models import ContactMessage
        from admissions.models import Candidature
        from mentorat.models import DemandeMentorat, MentorApplication
        from cours.models import Course
        from formation.models import Formation
        return {
            'sidebar_unread_contacts':             ContactMessage.objects.filter(status='unread').count(),
            'sidebar_pending_candidacies':         Candidature.objects.filter(statut='soumise').count(),
            'sidebar_pending_mentorships':         DemandeMentorat.objects.filter(statut='en_attente').count(),
            'sidebar_pending_mentor_applications': MentorApplication.objects.filter(status='pending').count(),
            'sidebar_draft_courses':               Course.objects.filter(status='draft').count(),
            'sidebar_draft_formations':            Formation.objects.filter(status='draft').count(),
        }
    except Exception:
        return {}
