"""
Template filter that processes [SANDBOX ...] markers in lesson content.
Usage: {{ lesson.contenu|process_sandbox_markers|safe }}

Marker syntax:
  [SANDBOX title="Try it" code="print('hello')"]
  [SANDBOX code="import numpy as np\nprint(np.pi)"]
"""
import re
import html
from django import template
from django.template.loader import render_to_string

register = template.Library()


@register.filter
def split(value, separator=','):
    """Split a string into a list: {{ "a,b,c"|split:"," }}"""
    return str(value).split(separator)

_SANDBOX_RE = re.compile(
    r'\[SANDBOX(?:\s+title="([^"]*)")?(?:\s+code="((?:[^"\\]|\\.)*)")?\s*\]',
    re.IGNORECASE,
)


@register.filter(name='process_sandbox_markers', is_safe=True)
def process_sandbox_markers(content, counter_start=0):
    """Replace [SANDBOX ...] markers with rendered sandbox widget HTML."""
    if not content:
        return content

    counter = [int(counter_start)]

    def replace_match(m):
        counter[0] += 1
        sid         = f'lesson_inline_{counter[0]}'
        title       = m.group(1) or 'Essaie toi-même'
        raw_code    = m.group(2) or '# Écris ton code ici\n'
        # Unescape any escaped quotes/backslashes from the marker
        decoded_code = raw_code.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')

        try:
            rendered = render_to_string('sandbox/sandbox_widget.html', {
                'sandbox_id':   sid,
                'title':        title,
                'initial_code': decoded_code,
                'height':       200,
                'show_save':    False,
                'show_packages': False,
                'readonly':     False,
            })
            return rendered
        except Exception:
            return f'<div class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-700">🐍 Sandbox: {html.escape(title)}</div>'

    return _SANDBOX_RE.sub(replace_match, content)
