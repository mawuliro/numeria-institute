"""
Content rendering pipeline: Markdown + LaTeX + HTML (sanitized).
Store raw text in DB; render at display time only via {{ content|render_content }}.

Supports Udemy-style callout boxes via blockquote markers:
  > 💡 **Astuce** : ...        → amber tip box
  > ⚠️ **Attention** : ...     → red warning box
  > ℹ️ **Info** : ...          → blue info box
  > ✅ **Exemple** : ...       → green example box
  > 📝 **Note** : ...          → slate note box
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
    'a', 'img', 'div', 'span', 'figure', 'figcaption',
    'sup', 'sub', 'mark', 'details', 'summary',
    'button', 'svg', 'path', 'circle', 'rect', 'polyline', 'polygon',
]

ALLOWED_ATTRS = {
    '*': ['class', 'id'],
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'code': ['class'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan'],
    'pre': ['class'],
    'button': ['type', 'onclick', 'class', 'title', 'data-code'],
    'svg': ['class', 'viewBox', 'width', 'height', 'fill', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin'],
    'path': ['d', 'fill', 'stroke', 'stroke-width'],
    'circle': ['cx', 'cy', 'r', 'fill', 'stroke', 'stroke-width', 'class'],
    'rect': ['x', 'y', 'width', 'height', 'rx', 'ry', 'fill', 'stroke'],
    'polyline': ['points', 'fill', 'stroke', 'stroke-width'],
    'polygon': ['points', 'fill', 'stroke', 'stroke-width'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

_FENCED = re.compile(r'```[\s\S]*?```')
_INLINE_CODE = re.compile(r'`[^`\n]+`')
_BLANK = re.compile(r'\{\{(blank_\w+)\}\}')

# Callout box patterns — convert blockquotes starting with emoji markers
_CALLOUT_MAP = {
    '💡': ('callout-tip', 'Astuce'),
    '⚠️': ('callout-warning', 'Attention'),
    'ℹ️': ('callout-info', 'Info'),
    '✅': ('callout-example', 'Exemple'),
    '📝': ('callout-note', 'Note'),
}


def _convert_callouts(text):
    """Convert blockquotes with emoji markers into HTML callout divs.
    
    Input:  > 💡 **Astuce** : Use range() for loops
    Output: <div class="callout callout-tip">...<p>Use range() for loops</p></div>
    """
    lines = text.split('\n')
    result = []
    in_callout = False
    callout_class = None
    callout_title = None
    callout_lines = []

    for line in lines:
        stripped = line.strip()

        # Check if this line starts a callout blockquote
        if stripped.startswith('> '):
            content = stripped[2:]
            # Check for emoji marker
            found = False
            for emoji, (cls, default_title) in _CALLOUT_MAP.items():
                if content.startswith(emoji):
                    if not in_callout:
                        in_callout = True
                        callout_class = cls
                        callout_lines = []
                        # Extract title from **Title** pattern or use default
                        title_match = re.match(rf'{re.escape(emoji)}\s*\*\*(.+?)\*\*', content)
                        callout_title = title_match.group(1) if title_match else default_title
                        # Get remaining text after title
                        remaining = re.sub(rf'{re.escape(emoji)}\s*\*\*.+?\*\*\s*:?\s*', '', content)
                        if remaining.strip():
                            callout_lines.append(remaining)
                    else:
                        callout_lines.append(content)
                    found = True
                    break
            if not found and in_callout:
                # Continuation of callout (no emoji, just > text)
                callout_lines.append(content)
        else:
            # Non-blockquote line — close any open callout
            if in_callout:
                html = _build_callout_html(callout_class, callout_title, callout_lines)
                result.append(html)
                in_callout = False
                callout_lines = []
            result.append(line)

    # Close any remaining callout
    if in_callout:
        html = _build_callout_html(callout_class, callout_title, callout_lines)
        result.append(html)

    return '\n'.join(result)


def _build_callout_html(cls, title, lines):
    """Build the HTML for a callout box."""
    content = '\n'.join(lines).strip()
    if not content:
        return ''
    # Render the content as markdown (inline only, no headings)
    try:
        rendered = markdown.markdown(content, extensions=['nl2br', 'fenced_code', 'tables'])
    except Exception:
        rendered = f'<p>{content}</p>'
    return f'<div class="callout {cls}"><div class="callout-header">{title}</div><div class="callout-body">{rendered}</div></div>'


@register.filter(name='render_content', is_safe=True)
def render_content(value):
    if not value:
        return mark_safe('')

    text = str(value)
    placeholders = {}
    counter = [0]

    def protect(match):
        key = f'ZQZPROT{counter[0]}ZQZ'
        placeholders[key] = match.group(0)
        counter[0] += 1
        return key

    text = _INLINE_CODE.sub(protect, text)
    text = _BLANK.sub(protect, text)

    def protect_latex(match):
        key = f'ZQZLATEX{counter[0]}ZQZ'
        placeholders[key] = match.group(0)
        counter[0] += 1
        return key

    text = re.sub(r'\$\$[\s\S]*?\$\$', protect_latex, text)
    text = re.sub(r'\\\[[\s\S]*?\\\]', protect_latex, text)
    text = re.sub(r'(?<!\$)\$(?!\$)[^\n$]+?\$', protect_latex, text)
    text = re.sub(r'\\\([\s\S]*?\\\)', protect_latex, text)

    # Convert callout blockquotes BEFORE markdown processing
    text = _convert_callouts(text)

    html = markdown.markdown(text, extensions=[
        'fenced_code', 'tables', 'nl2br', 'attr_list',
        'def_list', 'footnotes', 'toc',
    ])

    for key, val in placeholders.items():
        html = html.replace(key, val)

    # Add copy button + language label to fenced code blocks
    html = _enhance_code_blocks(html)

    html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=False,
    )
    return mark_safe(html)


def _enhance_code_blocks(html):
    """Add a header bar with language label and copy button to each <pre><code> block."""
    def replacer(match):
        full = match.group(0)
        # Extract language class if present
        lang_match = re.search(r'class="[^"]*language-(\w+)', full)
        lang = lang_match.group(1) if lang_match else 'python'
        # Extract the code content
        code_match = re.search(r'<code[^>]*>(.*?)</code>', full, re.DOTALL)
        code_content = code_match.group(1) if code_match else ''
        # Generate a unique ID for this block
        import hashlib
        block_id = 'cb_' + hashlib.md5(code_content[:50].encode()).hexdigest()[:8]

        return f'''<div class="code-block-wrapper rounded-xl overflow-hidden my-4 border border-slate-700 shadow-lg">
<div class="code-block-header flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
<span class="text-xs font-mono text-slate-400 flex items-center gap-2"><svg class="w-3.5 h-3.5 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>{lang}</span>
<button type="button" onclick="copyCodeBlock('{block_id}')" class="text-xs text-slate-400 hover:text-white transition-colors flex items-center gap-1"><svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copier</button>
</div>
<pre id="{block_id}" class="bg-slate-900 text-slate-100 font-mono text-sm px-4 py-3 overflow-auto leading-relaxed">{full.replace("<pre", "<pre").replace("</pre>", "</pre>")}</pre>
</div>'''

    # Match <pre>...<code...>...</code>...</pre> patterns
    pattern = re.compile(r'<pre([^>]*)>(.*?)</pre>', re.DOTALL)
    return pattern.sub(replacer, html)
