"""
Unified rich-content rendering: Markdown + LaTeX + HTML (sanitized).
Raw text is stored as-is; this filter runs at display time only.
"""
import re

import bleach
import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's', 'del',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'blockquote', 'hr',
    'pre', 'code', 'kbd', 'samp',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'a', 'img', 'figure', 'figcaption',
    'div', 'span', 'section', 'article',
    'sup', 'sub', 'mark',
    'details', 'summary',
    'iframe',
]

ALLOWED_ATTRIBUTES = {
    '*': ['class', 'id', 'style'],
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'iframe': ['src', 'width', 'height', 'frameborder', 'allowfullscreen', 'allow'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan'],
    'code': ['class'],
    'div': ['class', 'id', 'style'],
    'pre': ['class'],
}

_FENCED_CODE = re.compile(r'```[\s\S]*?```')
_INLINE_CODE = re.compile(r'`[^`\n]+`')
_BLOCK_MATH = re.compile(r'\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]')
_INLINE_MATH = re.compile(
    r'(?<!\$)\$(?!\$)([^$\n]+?)(?<!\$)\$(?!\$)|\\\([\s\S]*?\\\)'
)
_BLANK_PLACEHOLDER = re.compile(r'\{\{(blank_\w+)\}\}')


def _protect_pattern(content, pattern, prefix, store):
    counter = [0]

    def save(match):
        key = f'{prefix}{counter[0]}ENDPROT'
        store[key] = match.group(0)
        counter[0] += 1
        return key

    return pattern.sub(save, content)


@register.filter(name='render_markdown_content', is_safe=True)
def render_markdown_content(content):
    """Convert raw Markdown/LaTeX/HTML to safe HTML for templates."""
    if not content:
        return mark_safe('')

    protected = {}
    text = str(content)

    # Protect code first so LaTeX inside code blocks is not touched
    text = _protect_pattern(text, _FENCED_CODE, 'CODEBLOCK', protected)
    text = _protect_pattern(text, _INLINE_CODE, 'CODEINLINE', protected)
    text = _protect_pattern(text, _BLANK_PLACEHOLDER, 'BLANKSLOT', protected)
    text = _protect_pattern(text, _BLOCK_MATH, 'LATEXBLOCK', protected)
    text = _protect_pattern(text, _INLINE_MATH, 'LATEXINLINE', protected)

    html = markdown.markdown(
        text,
        extensions=[
            'fenced_code',
            'codehilite',
            'tables',
            'nl2br',
            'toc',
            'attr_list',
            'def_list',
            'footnotes',
            'admonition',
            'meta',
        ],
        extension_configs={
            'codehilite': {
                'css_class': 'highlight',
                'guess_lang': True,
                'use_pygments': False,
            },
            'toc': {
                'permalink': True,
            },
        },
    )

    for key, value in protected.items():
        html = html.replace(key, value)

    html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=False,
    )

    return mark_safe(html)
