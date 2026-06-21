import os
import logging
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from .utils import staff_only

logger = logging.getLogger(__name__)


@staff_only
def media_list(request):
    from admin_panel.models import UploadedMedia
    qs = UploadedMedia.objects.select_related('uploaded_by').all()

    type_f = request.GET.get('type', '')
    if type_f:
        qs = qs.filter(media_type=type_f)

    paginator = Paginator(qs, 24)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_panel/media_library.html', {
        'page_obj': page_obj,
        'type_f':   type_f,
    })


@staff_only
@require_POST
def media_upload(request):
    from admin_panel.models import UploadedMedia
    files  = request.FILES.getlist('files') or request.FILES.getlist('file')
    result = []
    for f in files:
        ext   = os.path.splitext(f.name)[1].lower()
        mtype = ('image' if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')
                 else 'pdf' if ext == '.pdf' else 'other')
        m = UploadedMedia.objects.create(
            file=f, name=f.name[:200],
            media_type=mtype, uploaded_by=request.user,
            file_size=f.size,
        )
        result.append({'id': m.id, 'name': m.name, 'url': m.file.url, 'type': m.media_type})
    return JsonResponse({'ok': True, 'files': result})


@staff_only
@require_POST
def media_delete(request, media_id):
    from admin_panel.models import UploadedMedia
    media = get_object_or_404(UploadedMedia, id=media_id)
    try:
        if media.file:
            media.file.delete(save=False)
    except Exception:
        pass
    media.delete()
    return JsonResponse({'ok': True})
