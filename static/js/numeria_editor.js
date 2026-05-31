/**
 * Numeria Institute — unified EasyMDE editor for rich content (Markdown + LaTeX + HTML).
 * Load EasyMDE, marked.js, MathJax, and Prism once per page before calling initNumeriaEditor().
 */
function initNumeriaEditor(elementId, opts) {
  opts = opts || {};
  const el = typeof elementId === 'string'
    ? document.getElementById(elementId)
    : elementId;
  if (!el || el.dataset.numeriaEditorInit) return null;
  if (typeof EasyMDE === 'undefined') {
    console.warn('EasyMDE is not loaded.');
    return null;
  }

  const editor = new EasyMDE({
    element: el,
    spellChecker: false,
    minHeight: opts.height || '200px',
    placeholder: opts.placeholder || 'Écris ici en Markdown, LaTeX ou HTML…',
    toolbar: opts.toolbar || [
      'bold', 'italic', 'strikethrough', '|',
      'heading-2', 'heading-3', '|',
      'unordered-list', 'ordered-list', '|',
      'link', 'image', 'table', '|',
      'code', 'quote', '|',
      {
        name: 'latex-inline',
        action: function(ed) {
          const cm = ed.codemirror;
          const sel = cm.getSelection() || 'formule';
          cm.replaceSelection('$' + sel + '$');
        },
        title: 'LaTeX inline $...$',
        text: '∑',
      },
      {
        name: 'latex-block',
        action: function(ed) {
          const cm = ed.codemirror;
          cm.replaceSelection('\n$$\n' + (cm.getSelection() || '\\int_0^1 f(x)\\,dx') + '\n$$\n');
        },
        title: 'LaTeX bloc $$...$$',
        text: '∫',
      },
      {
        name: 'python',
        action: function(ed) {
          const cm = ed.codemirror;
          cm.replaceSelection('\n```python\n' + (cm.getSelection() || '# code ici') + '\n```\n');
        },
        title: 'Bloc Python',
        text: '🐍',
      },
      '|', 'preview', 'side-by-side', 'fullscreen',
    ],
    previewRender: function(text, preview) {
      if (window.marked && typeof window.marked.parse === 'function') {
        preview.innerHTML = window.marked.parse(text);
      } else if (EasyMDE.prototype.markdown) {
        preview.innerHTML = EasyMDE.prototype.markdown(text);
      } else {
        preview.innerHTML = text.replace(/\n/g, '<br>');
      }
      setTimeout(function() {
        if (window.MathJax && MathJax.typesetPromise) {
          MathJax.typesetClear([preview]);
          MathJax.typesetPromise([preview]).catch(function() {});
        }
        if (window.Prism && Prism.highlightAllUnder) {
          Prism.highlightAllUnder(preview);
        }
      }, 50);
      return preview.innerHTML;
    },
  });

  editor.codemirror.on('change', function() {
    clearTimeout(editor._previewTimer);
    editor._previewTimer = setTimeout(function() {
      const prev = document.querySelector('.editor-preview-side, .editor-preview');
      if (!prev) return;
      if (window.MathJax && MathJax.typesetPromise) {
        MathJax.typesetClear([prev]);
        MathJax.typesetPromise([prev]).catch(function() {});
      }
      if (window.Prism && Prism.highlightAllUnder) {
        Prism.highlightAllUnder(prev);
      }
    }, 600);
  });

  el.dataset.numeriaEditorInit = '1';
  return editor;
}

/** Backward compatibility with previous editor.js */
window.NumeriaMarkdown = window.NumeriaMarkdown || {};
window.NumeriaMarkdown.initEditor = initNumeriaEditor;
window.NumeriaMarkdown.createMarkdownEditor = function(textarea, opts) {
  if (textarea && !textarea.id) {
    textarea.id = 'numeria-ed-' + Math.random().toString(36).slice(2, 9);
  }
  return initNumeriaEditor(textarea, opts || {});
};
