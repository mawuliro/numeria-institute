"""
Sandbox views — Python IDE available to all authenticated users.
Also includes the staff-only admin sandbox.
"""
import json
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST, require_GET

from .utils import staff_only

logger = logging.getLogger(__name__)


# ─── USER SANDBOX ─────────────────────────────────────────────────────────────

@login_required
def sandbox_page(request):
    from cours.models import UserScript
    scripts = UserScript.objects.filter(user=request.user)
    return render(request, 'sandbox/sandbox_page.html', {'scripts': scripts})


@login_required
@require_POST
def sandbox_save_script(request):
    from cours.models import UserScript
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()

    script_id = data.get('id')
    titre     = data.get('titre', 'Sans titre').strip() or 'Sans titre'
    code      = data.get('code', '')

    if script_id:
        script = get_object_or_404(UserScript, id=script_id, user=request.user)
        script.titre = titre
        script.code  = code
        script.save()
    else:
        script = UserScript.objects.create(user=request.user, titre=titre, code=code)

    return JsonResponse({'ok': True, 'id': script.id, 'titre': script.titre})


@login_required
@require_GET
def sandbox_load_script(request, script_id):
    from cours.models import UserScript
    script = get_object_or_404(UserScript, id=script_id, user=request.user)
    return JsonResponse({'id': script.id, 'titre': script.titre, 'code': script.code})


@login_required
@require_POST
def sandbox_delete_script(request, script_id):
    from cours.models import UserScript
    get_object_or_404(UserScript, id=script_id, user=request.user).delete()
    return JsonResponse({'ok': True})


@login_required
@require_GET
def sandbox_list_scripts(request):
    from cours.models import UserScript
    scripts = list(
        UserScript.objects.filter(user=request.user).values('id', 'titre', 'updated_at')
    )
    for s in scripts:
        s['updated_at'] = s['updated_at'].strftime('%d/%m/%Y %H:%M')
    return JsonResponse({'scripts': scripts})


# ─── ADMIN SANDBOX ────────────────────────────────────────────────────────────

@staff_only
def admin_sandbox(request):
    from cours.models import UserScript
    scripts = UserScript.objects.filter(user=request.user)
    return render(request, 'sandbox/sandbox_admin.html', {'scripts': scripts})
