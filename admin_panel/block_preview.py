"""
Safe LessonBlock serializer for staff preview pages.

The LessonBlock / exercise models do not expose a get_payload() method, so this
module builds plain dicts the preview template can render. It NEVER exposes
solution_code or test_code (Rule: do not leak solutions to the browser).
"""


def _embed_youtube(url):
    """Return an embeddable iframe URL for common YouTube/Vimeo links."""
    if not url:
        return ''
    u = url.strip()
    if 'youtube.com/watch' in u and 'v=' in u:
        vid = u.split('v=', 1)[1].split('&', 1)[0]
        return f'https://www.youtube.com/embed/{vid}'
    if 'youtu.be/' in u:
        vid = u.split('youtu.be/', 1)[1].split('?', 1)[0]
        return f'https://www.youtube.com/embed/{vid}'
    if 'vimeo.com/' in u and '/embed/' not in u:
        vid = u.rstrip('/').split('/')[-1]
        return f'https://player.vimeo.com/video/{vid}'
    return u


def build_block_previews(*, course_lesson=None, formation_lesson=None):
    """
    Return a list of dicts describing each block of a lesson for preview.

    Exactly one of course_lesson / formation_lesson must be provided.
    """
    from cours.models import LessonBlock

    if bool(course_lesson) == bool(formation_lesson):
        return []

    filter_kw = (
        {'course_lesson': course_lesson}
        if course_lesson else
        {'formation_lesson': formation_lesson}
    )
    blocks = LessonBlock.objects.filter(**filter_kw).order_by('order')

    out = []
    for block in blocks:
        data = {'id': block.id, 'type': block.block_type}

        if block.block_type == 'text':
            data['text_content'] = block.text_content or ''

        elif block.block_type == 'video':
            data['video_url'] = _embed_youtube(block.video_url)
            data['video_caption'] = block.video_caption or ''

        elif block.block_type == 'sandbox':
            data['sandbox_title'] = block.sandbox_title or 'Essaie toi-même'
            data['sandbox_initial_code'] = block.sandbox_initial_code or ''

        else:
            # Exercise blocks — expose only safe public fields.
            ex = (
                block.code_exercise or block.mcq_exercise or block.fill_blank
                or block.true_false or block.code_order or block.matching
                or block.short_answer
            )
            if ex:
                data['exercise'] = {
                    'title': ex.title,
                    'instructions': getattr(ex, 'instructions', '') or '',
                    'difficulty': ex.get_difficulty_display(),
                    'points': ex.points,
                }
            else:
                data['exercise'] = None

        out.append(data)

    return out
