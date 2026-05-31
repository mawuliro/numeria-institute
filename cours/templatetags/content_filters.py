"""
Content rendering pipeline: Markdown + LaTeX + HTML (sanitized).
Store raw text in DB; render at display time only via {{ content|render_content }}.
"""
import re

import bleach
import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's', 'del', 'code', 'pre', 'kbd',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'blockquote', 'hr',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'a', 'img', 'iframe', 'div', 'span', 'figure', 'figcaption',
    'sup', 'sub', 'mark', 'details', 'summary',
]

ALLOWED_ATTRS = {
    '*': ['class', 'id', 'style'],
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'iframe': ['src', 'width', 'height', 'frameborder', 'allowfullscreen', 'allow'],
    'code': ['class'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan'],
    'pre': ['class'],
}

_FENCED = re.compile(r'```[\s\S]*?```')
_INLINE_CODE = re.compile(r'`[^`\n]+`')
_BLANK = re.compile(r'\{\{(blank_\w+)\}\}')


@register.filter(name='render_content', is_safe=True)
def render_content(value):
    if not value:
        return mark_safe('')

    text = str(value)
    placeholders = {}
    counter = [0]

    def protect(match):
        key = f'__PROT{counter[0]}__'
        placeholders[key] = match.group(0)
        counter[0] += 1
        return key

    # Protect code and blanks before LaTeX
    text = _FENCED.sub(protect, text)
    text = _INLINE_CODE.sub(protect, text)
    text = _BLANK.sub(protect, text)

    def protect_latex(match):
        key = f'__LATEX{counter[0]}__'
        placeholders[key] = match.group(0)
        counter[0] += 1
        return key

    text = re.sub(r'\$\$[\s\S]*?\$\$', protect_latex, text)
    text = re.sub(r'\\\[[\s\S]*?\\\]', protect_latex, text)
    text = re.sub(r'(?<!\$)\$(?!\$)[^\n$]+?\$', protect_latex, text)
    text = re.sub(r'\\\([\s\S]*?\\\)', protect_latex, text)

    html = markdown.markdown(text, extensions=[
        'fenced_code', 'tables', 'nl2br', 'attr_list',
        'def_list', 'footnotes', 'toc',
    ])

    for key, val in placeholders.items():
        html = html.replace(key, val)

    html = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=False)
    return mark_safe(html)
