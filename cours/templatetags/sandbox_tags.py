"""
Template filters for lesson content:
- split: split a string by separator
- render_content: Markdown + LaTeX + HTML + sandbox markers
- process_sandbox_markers: replace [SANDBOX ...] markers with rendered widgets
"""
import html as html_module
import re

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from cours.templatetags.content_filters import render_markdown_content

register = template.Library()


@register.filter
def split(value, separator=','):
    """Split a string into a list: {{ "a,b,c"|split:"," }}"""
    return str(value).split(separator)


@register.filter(name='render_markdown_latex', is_safe=True)
def render_markdown_latex(content):
    """Alias for render_markdown_content (backward compatibility)."""
    return render_markdown_content(content)


@register.filter(name='render_content', is_safe=True)
def render_content(content):
    """Render content with Markdown, HTML, LaTeX and sandbox markers."""
    if not content:
        return mark_safe('')
    content = process_sandbox_markers(content)
    return render_markdown_content(content)


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
        sid = f'lesson_inline_{counter[0]}'
        title = m.group(1) or 'Essaie toi-même'
        raw_code = m.group(2) or '# Écris ton code ici\n'
        decoded_code = (
            raw_code.replace('\\"', '"')
            .replace('\\n', '\n')
            .replace('\\t', '\t')
            .replace('\\\\', '\\')
        )

        try:
            rendered = render_to_string('sandbox/sandbox_widget.html', {
                'sandbox_id': sid,
                'title': title,
                'initial_code': decoded_code,
                'height': 200,
                'show_save': False,
                'show_packages': False,
                'readonly': False,
            })
            return rendered
        except Exception:
            return (
                f'<div class="bg-amber-50 border border-amber-200 rounded-lg p-3 '
                f'text-sm text-amber-700">🐍 Sandbox: {html_module.escape(title)}</div>'
            )

    return _SANDBOX_RE.sub(replace_match, content)
