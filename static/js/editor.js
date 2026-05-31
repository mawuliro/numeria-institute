(function() {
  'use strict';

  const PRISM_CSS = 'https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css';
  const PRISM_JS = 'https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js';
  const PRISM_AUTO = 'https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/autoloader/prism-autoloader.min.js';

  const DEFAULT_TOOLBAR = [
    'bold', 'italic', 'strikethrough', '|',
    'heading-2', 'heading-3', '|',
    'unordered-list', 'ordered-list', '|',
    'link', 'image', '|',
    'code', 'quote', '|',
    {
      name: 'latex-inline',
      action: function(editor) {
        const cm = editor.codemirror;
        const sel = cm.getSelection();
        cm.replaceSelection('$' + (sel || 'formule') + '$');
      },
      className: 'fa fa-superscript',
      title: 'LaTeX inline ($...$)',
      text: '∑',
    },
    {
      name: 'latex-block',
      action: function(editor) {
        const cm = editor.codemirror;
        const sel = cm.getSelection();
        cm.replaceSelection('\n$$\n' + (sel || '\\int_0^1 f(x)\\,dx') + '\n$$\n');
      },
      className: 'fa fa-calculator',
      title: 'LaTeX bloc ($$...$$)',
      text: '∫',
    },
    {
      name: 'python-code',
      action: function(editor) {
        const cm = editor.codemirror;
        const sel = cm.getSelection();
        cm.replaceSelection('\n```python\n' + (sel || '# votre code ici') + '\n```\n');
      },
      className: 'fa fa-code',
      title: 'Bloc de code Python',
      text: '🐍',
    },
    {
      name: 'sandbox',
      action: function(editor) {
        editor.codemirror.replaceSelection(
          '[SANDBOX title="Essaie toi-même" code="# Écris ton code ici\\n"]'
        );
      },
      className: 'fa fa-play-circle',
      title: 'Insérer un sandbox Python interactif',
      text: '▶',
    },
    '|',
    'preview', 'side-by-side', 'fullscreen', '|',
    'guide',
  ];

  const COMPACT_TOOLBAR = [
    'bold', 'italic', '|',
    {
      name: 'latex-inline',
      action: function(editor) {
        const cm = editor.codemirror;
        const sel = cm.getSelection();
        cm.replaceSelection('$' + (sel || 'x') + '$');
      },
      title: 'LaTeX inline',
      text: '∑',
    },
  ];

  const DEFAULT_PLACEHOLDER =
    'Écris ici en Markdown...\n\n' +
    'Exemples :\n**gras**, *italique*, `code`\n\n' +
    'LaTeX inline : $E = mc^2$\n\n' +
    'LaTeX bloc :\n$$\n\\int_0^\\infty e^{-x^2} dx\n$$\n\n' +
    'Code Python :\n```python\nprint("Hello")\n```';

  function loadCss(href) {
    if (document.querySelector('link[href="' + href + '"]')) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    document.head.appendChild(link);
  }

  function loadScript(src) {
    return new Promise(function(resolve, reject) {
      if (document.querySelector('script[src="' + src + '"]')) {
        resolve();
        return;
      }
      const script = document.createElement('script');
      script.src = src;
      script.async = true;
      script.onload = function() { resolve(); };
      script.onerror = function() { reject(new Error('Failed to load ' + src)); };
      document.head.appendChild(script);
    });
  }

  function ensurePrism() {
    window.NumeriaMarkdown = window.NumeriaMarkdown || {};
    if (!window.NumeriaMarkdown._prismPromise) {
      loadCss(PRISM_CSS);
      window.NumeriaMarkdown._prismPromise = loadScript(PRISM_JS)
        .then(function() { return loadScript(PRISM_AUTO); })
        .catch(function() { return null; });
    }
    return window.NumeriaMarkdown._prismPromise;
  }

  function markdownToHtml(plainText) {
    if (window.marked && typeof window.marked.parse === 'function') {
      return window.marked.parse(plainText);
    }
    if (window.EasyMDE && EasyMDE.prototype.markdown) {
      return EasyMDE.prototype.markdown(plainText);
    }
    return plainText.replace(/\n/g, '<br>');
  }

  function refreshPreviewPanels() {
    const panels = document.querySelectorAll('.editor-preview-side, .editor-preview');
    if (!panels.length) return;
    if (window.MathJax && typeof MathJax.typesetPromise === 'function') {
      MathJax.typesetClear(Array.from(panels));
      MathJax.typesetPromise(Array.from(panels)).catch(function(err) {
        console.log('MathJax error:', err);
      });
    }
    if (window.Prism && typeof Prism.highlightAllUnder === 'function') {
      panels.forEach(function(panel) { Prism.highlightAllUnder(panel); });
    }
  }

  function createSyntaxGuide() {
    const details = document.createElement('details');
    details.className = 'syntax-guide';
    details.innerHTML =
      '<summary>📖 Guide de syntaxe</summary>' +
      '<div class="syntax-grid">' +
        '<div>' +
          '<strong>Markdown</strong><br>' +
          '**gras** → <strong>gras</strong><br>' +
          '*italique* → <em>italique</em><br>' +
          '# Titre H1<br>' +
          '## Titre H2<br>' +
          '- liste<br>' +
          '<code>code inline</code><br>' +
          '[lien](url)<br>' +
          '![image](url)' +
        '</div>' +
        '<div>' +
          '<strong>LaTeX</strong><br>' +
          '$E = mc^2$ → inline<br>' +
          '$$\\int_0^1 x dx$$ → bloc<br>' +
          '$\\frac{a}{b}$ → fraction<br>' +
          '$\\sqrt{x}$ → racine<br>' +
          '$x^{n}$ → exposant<br>' +
          '$x_{i}$ → indice<br>' +
          '$\\sum_{i=0}^{n}$ → somme' +
        '</div>' +
        '<div>' +
          '<strong>Code</strong><br>' +
          '```python<br>print("hello")<br>```<br><br>' +
          '<strong>Sandbox</strong><br>' +
          '[SANDBOX title="..." code="..."]<br><br>' +
          '<strong>HTML direct</strong><br>' +
          '&lt;table&gt;...&lt;/table&gt;<br>' +
          '&lt;iframe src="..."&gt;' +
        '</div>' +
      '</div>';
    return details;
  }

  function attachSyntaxGuide(editor) {
    const container = editor.codemirror.getWrapperElement().closest('.EasyMDEContainer');
    if (!container || container.querySelector('.syntax-guide')) return;
    container.parentNode.insertBefore(createSyntaxGuide(), container.nextSibling);
  }

  function wirePreviewDebounced(editor) {
    if (!editor || !editor.codemirror || editor.codemirror._numeriaPreviewWired) return;
    editor.codemirror._numeriaPreviewWired = true;
    editor.codemirror.on('change', function() {
      clearTimeout(window._numeriaPreviewTimer);
      window._numeriaPreviewTimer = setTimeout(refreshPreviewPanels, 800);
    });
  }

  function imageUploadFunction(imageUploadUrl, csrfToken) {
    if (!imageUploadUrl) return undefined;
    return function(file, onSuccess, onError) {
      const fd = new FormData();
      fd.append('file', file);
      fetch(imageUploadUrl, {
        method: 'POST',
        headers: csrfToken ? { 'X-CSRFToken': csrfToken } : {},
        body: fd,
      })
        .then(function(r) { return r.json(); })
        .then(function(d) {
          if (d.ok) onSuccess(d.url);
          else onError(d.error || 'Upload failed');
        })
        .catch(function() { onError('Upload failed'); });
    };
  }

  function previewRender(plainText, preview) {
    preview.innerHTML = '<em>Chargement de l\'aperçu...</em>';
    const html = markdownToHtml(plainText);
    preview.innerHTML = html;
    setTimeout(function() {
      refreshPreviewPanels();
    }, 60);
    return preview.innerHTML;
  }

  function initEditor(elementId, options) {
    options = options || {};
    const el = typeof elementId === 'string'
      ? document.getElementById(elementId)
      : elementId;
    if (!el || el.dataset.numeriaEditorInit) return null;
    if (typeof EasyMDE === 'undefined') {
      console.warn('EasyMDE is not loaded yet.');
      return null;
    }

    const compact = options.compact || el.dataset.compactEditor === '1';
    const config = Object.assign({
      element: el,
      spellChecker: false,
      autosave: {
        enabled: options.autosave || false,
        uniqueId: el.id || ('editor-' + Date.now()),
        delay: 5000,
      },
      toolbar: compact ? COMPACT_TOOLBAR : DEFAULT_TOOLBAR,
      previewRender: previewRender,
      minHeight: options.height || options.minHeight || '300px',
      placeholder: options.placeholder || DEFAULT_PLACEHOLDER,
      imageUploadFunction: imageUploadFunction(
        options.imageUploadUrl || el.dataset.imageUploadUrl,
        options.csrfToken || el.dataset.csrfToken
      ),
    }, options.config || {});

    if (options.toolbar) config.toolbar = options.toolbar;

    const editor = new EasyMDE(config);
    el.dataset.numeriaEditorInit = '1';
    attachSyntaxGuide(editor);
    wirePreviewDebounced(editor);
    ensurePrism();
    return editor;
  }

  function createMarkdownEditor(textarea, opts) {
    opts = opts || {};
    if (!textarea) return null;
    if (!textarea.id) {
      textarea.id = 'numeria-editor-' + Math.random().toString(36).slice(2, 9);
    }
    return initEditor(textarea, Object.assign({}, opts, {
      height: opts.minHeight || opts.height,
      imageUploadUrl: opts.imageUploadUrl || textarea.dataset.imageUploadUrl,
      csrfToken: opts.csrfToken || textarea.dataset.csrfToken,
    }));
  }

  function initRichEditors(root) {
    (root || document).querySelectorAll('textarea[data-rich-editor]').forEach(function(ta) {
      initEditor(ta, {
        compact: ta.dataset.compactEditor === '1',
        height: ta.dataset.editorHeight || '280px',
        imageUploadUrl: ta.dataset.imageUploadUrl,
        csrfToken: ta.dataset.csrfToken,
      });
    });
  }

  window.NumeriaMarkdown = window.NumeriaMarkdown || {};
  window.NumeriaMarkdown.initEditor = initEditor;
  window.NumeriaMarkdown.createMarkdownEditor = createMarkdownEditor;
  window.NumeriaMarkdown.initRichEditors = initRichEditors;
  window.NumeriaMarkdown.refreshPreviewPanels = refreshPreviewPanels;

  document.addEventListener('DOMContentLoaded', function() {
    initRichEditors();
  });
})();
