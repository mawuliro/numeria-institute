"""
Template filters for lesson content:
- split: split a string by separator
- render_markdown_latex: Markdown → HTML with LaTeX preservation
- process_sandbox_markers: replace [SANDBOX ...] markers with rendered widgets
"""
import re
import html as html_module
from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def split(value, separator=','):
    """Split a string into a list: {{ "a,b,c"|split:"," }}"""
    return str(value).split(separator)


# ── LaTeX-safe Markdown renderer ──────────────────────────────────────────────

_BLOCK_MATH  = re.compile(r'\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]')
_INLINE_MATH = re.compile(r'(?<!\$)\$(?!\$)[^\$\n]+?\$(?!\$)|\\\(.+?\\\)')


def _protect_latex(content):
    """Replace LaTeX fragments with unique ASCII placeholders before Markdown processing."""
    placeholders = {}
    counter      = [0]

    def save(m):
        key = f'NUMERIAMATHSLOT{counter[0]}ENDSLOT'
        placeholders[key] = m.group(0)
        counter[0] += 1
        return key

    text = _BLOCK_MATH.sub(save, content)
    text = _INLINE_MATH.sub(save, text)
    return text, placeholders


@register.filter(name='render_markdown_latex', is_safe=True)
def render_markdown_latex(content):
    """
    Convert Markdown to HTML while preserving LaTeX delimiters for MathJax.

    Supports: $...$ inline, $$...$$ block, \\(...\\), \\[...\\]
    Uses markdown-it-py (already in requirements.txt).
    """
    if not content:
        return mark_safe('')
    try:
        from markdown_it import MarkdownIt
        protected, placeholders = _protect_latex(content)
        md   = MarkdownIt()
        html = md.render(protected)
        for key, value in placeholders.items():
            html = html.replace(key, value)
        return mark_safe(html)
    except ImportError:
        return mark_safe(content)

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
