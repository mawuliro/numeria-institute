/**
 * Numeria Admin — shared lesson block builder + helpers for course/formation editors.
 * Requires: NumeriaMarkdown (editor.js), EasyMDE, optional CodeMirror.
 * Set window.NumeriaAdminConfig = { csrf, imgUrl } before loading this script.
 */
'use strict';

(function() {
  var cfg = window.NumeriaAdminConfig || {};
  var CSRF = cfg.csrf || '';
  var IMG_URL = cfg.imgUrl || '';

  var lbMdes = {};
  var lbCms = {};
  var lbDragId = null;
  var lbAutoSaveTm = null;
  var lbLessonId = null;
  var lbLessonType = null;
  var mcqChoiceCount = {};

  function now() {
    return new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  }

  function editorOpts(extra) {
    return Object.assign({
      imageUploadUrl: IMG_URL,
      csrfToken: CSRF,
    }, extra || {});
  }

  /* ── Block builder ─────────────────────────────────────────────────────── */

  async function loadLessonBlocks(lessonId, lessonType) {
    lbLessonId = lessonId;
    lbLessonType = lessonType;
    var url = lessonType === 'formation'
      ? '/fr/admin-panel/formation-lessons/' + lessonId + '/blocks/'
      : '/fr/admin-panel/lessons/' + lessonId + '/blocks/';
    var r = await fetch(url, { headers: { 'X-CSRFToken': CSRF } });
    var data = await r.json();
    var cont = document.getElementById('lb-container');
    if (cont) {
      cont.innerHTML = data.html || '';
      lbInitAll();
      lbStartAutoSave();
    }
  }

  function lbInitAll() {
    document.querySelectorAll('.lb-mde-target').forEach(function(ta) {
      var bid = ta.dataset.blockId;
      if (!bid || lbMdes[bid]) return;
      var mde = window.NumeriaMarkdown.createMarkdownEditor(ta, editorOpts({
        toolbar: ['bold', 'italic', 'heading-2', '|', 'unordered-list', 'ordered-list', '|',
          'link', 'image', 'code', 'quote', '|',
          { name: 'latex', action: function(e) { e.codemirror.replaceSelection('$$\n\n$$'); }, className: 'fa', title: '∑ LaTeX' },
          '|', 'preview', 'side-by-side'],
      }));
      if (mde && mde.codemirror) {
        mde.codemirror.on('change', function() { lbSetSaveStatus(bid, ''); });
      }
      lbMdes[bid] = mde;
    });

    document.querySelectorAll('.lb-cm-target').forEach(function(wrap) {
      var bid = wrap.dataset.blockId;
      if (!bid || lbCms[bid]) return;
      var ta = document.getElementById('lb-cm-ta-' + bid);
      if (!ta || !window.CodeMirror) return;
      var cm = CodeMirror(wrap, {
        value: ta.value,
        mode: 'python', theme: 'dracula', lineNumbers: true,
        indentUnit: 4, tabSize: 4, indentWithTabs: false,
        lineWrapping: true, viewportMargin: Infinity, autoCloseBrackets: true,
        extraKeys: { Tab: function(c) { c.replaceSelection('    ', 'end'); } },
      });
      cm.getWrapperElement().style.minHeight = '120px';
      cm.on('change', function() { lbSetSaveStatus(bid, ''); });
      lbCms[bid] = cm;
    });

    document.querySelectorAll('.lb-field').forEach(function(input) {
      input.addEventListener('input', function() {
        var card = input.closest('[data-block-id]');
        if (card) lbSetSaveStatus(card.dataset.blockId, '');
      });
    });
  }

  function lbSetSaveStatus(bid, msg) {
    var el = document.querySelector('.lb-save-status[data-block-id="' + bid + '"]');
    if (el) el.textContent = msg;
  }

  async function lbSaveBlock(blockId) {
    var body = {};
    var card = document.querySelector('.lb-card[data-block-id="' + blockId + '"]');
    if (!card) return;
    card.querySelectorAll('.lb-field').forEach(function(f) {
      body[f.dataset.field] = f.value;
    });
    if (lbMdes[blockId]) body.text_content = lbMdes[blockId].value();
    if (lbCms[blockId]) body.sandbox_initial_code = lbCms[blockId].getValue();

    var r = await fetch('/fr/admin-panel/blocks/' + blockId + '/update/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify(body),
    });
    var d = await r.json();
    if (d.success) {
      lbSetSaveStatus(blockId, '✓ sauvegardé — ' + now());
      if (window.setAutosaveText) window.setAutosaveText('Blocs sauvegardés ✓ — ' + now());
    }
  }

  async function lbAddBlock(blockType, position) {
    if (!lbLessonId) return;
    var url = lbLessonType === 'formation'
      ? '/fr/admin-panel/formation-lessons/' + lbLessonId + '/blocks/add/'
      : '/fr/admin-panel/lessons/' + lbLessonId + '/blocks/add/';
    var r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({ block_type: blockType, position: position }),
    });
    var data = await r.json();
    var list = document.getElementById('lb-list');
    var empty = document.getElementById('lb-empty');
    if (empty) empty.remove();
    if (list && data.html) {
      var tmp = document.createElement('div');
      tmp.innerHTML = data.html;
      var card = tmp.firstElementChild;
      if (card) {
        if (position != null && position >= 0) {
          var cards = list.querySelectorAll('.lb-card[data-block-id]');
          if (cards[position]) {
            list.insertBefore(card, cards[position]);
          } else {
            list.appendChild(card);
          }
        } else {
          list.appendChild(card);
        }
      }
      lbInitAll();
    }
  }

  function lbShowAddMenu(position, event) {
    if (event) event.stopPropagation();
    var types = [
      ['text', '📝 Texte'], ['video', '🎬 Vidéo'], ['sandbox', '🐍 Sandbox'],
      ['exercise', '💻 Exercice'], ['mcq', '🔘 QCM'], ['fill_blank', '✏️ Trous'],
      ['true_false', '✅ V/F'], ['code_order', '🧩 Ordre'], ['matching', '🔗 Asso.'],
      ['short_answer', '💬 Court'],
    ];
    var existing = document.getElementById('lb-add-menu');
    if (existing) existing.remove();

    var menu = document.createElement('div');
    menu.id = 'lb-add-menu';
    menu.className = 'fixed z-50 bg-white border border-slate-200 rounded-xl shadow-lg p-2 grid grid-cols-2 gap-1 text-xs';
    menu.style.minWidth = '200px';
    types.forEach(function(pair) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'text-left px-3 py-2 rounded-lg hover:bg-sky-50 text-slate-700';
      btn.textContent = pair[1];
      btn.onclick = function() {
        menu.remove();
        lbAddBlock(pair[0], position);
      };
      menu.appendChild(btn);
    });

    document.body.appendChild(menu);
    if (event && event.clientX) {
      menu.style.left = Math.min(event.clientX, window.innerWidth - 220) + 'px';
      menu.style.top = event.clientY + 'px';
    } else {
      menu.style.left = '50%';
      menu.style.top = '40%';
      menu.style.transform = 'translate(-50%, -50%)';
    }

    setTimeout(function() {
      document.addEventListener('click', function closeMenu() {
        menu.remove();
        document.removeEventListener('click', closeMenu);
      }, { once: true });
    }, 0);
  }

  async function lbDeleteBlock(blockId) {
    if (!confirm('Supprimer ce bloc ?')) return;
    var r = await fetch('/fr/admin-panel/blocks/' + blockId + '/delete/', {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
      body: '{}',
    });
    var d = await r.json();
    if (d.success) {
      document.querySelector('.lb-card[data-block-id="' + blockId + '"]')?.remove();
      delete lbMdes[blockId];
      delete lbCms[blockId];
    }
  }

  function lbToggle(header) {
    var body = header.nextElementSibling;
    var icon = header.querySelector('.lb-collapse-icon');
    if (body) body.classList.toggle('hidden');
    if (icon) icon.textContent = body && body.classList.contains('hidden') ? '▶' : '▼';
  }

  function lbDragStart(e, blockId) { lbDragId = blockId; e.dataTransfer.effectAllowed = 'move'; }
  function lbDragOver(e) { e.preventDefault(); e.currentTarget.classList.add('ring-2', 'ring-sky-400'); }
  function lbDragLeave(e) { e.currentTarget.classList.remove('ring-2', 'ring-sky-400'); }
  function lbDrop(e, targetId) {
    e.preventDefault();
    e.currentTarget.classList.remove('ring-2', 'ring-sky-400');
    if (!lbDragId || lbDragId === targetId) return;
    var src = document.querySelector('.lb-card[data-block-id="' + lbDragId + '"]');
    var tgt = document.querySelector('.lb-card[data-block-id="' + targetId + '"]');
    if (src && tgt) tgt.parentNode.insertBefore(src, tgt);
    lbSaveBlockOrder();
  }

  async function lbSaveBlockOrder() {
    if (!lbLessonId) return;
    var order = [];
    document.querySelectorAll('.lb-card[data-block-id]').forEach(function(c) {
      order.push(+c.dataset.blockId);
    });
    var url = lbLessonType === 'formation'
      ? '/fr/admin-panel/formation-lessons/' + lbLessonId + '/blocks/reorder/'
      : '/fr/admin-panel/lessons/' + lbLessonId + '/blocks/reorder/';
    await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({ order: order }),
    });
    if (window.nbToast) nbToast('Ordre sauvegardé ✓', 'success');
  }

  function lbUpdatePreview(blockId, url) {
    var wrap = document.getElementById('lb-vid-preview-' + blockId);
    var frame = wrap ? wrap.querySelector('iframe') : null;
    if (!wrap || !frame) return;
    if (url) { frame.src = url; wrap.classList.remove('hidden'); }
    else { wrap.classList.add('hidden'); }
  }

  function lbStartAutoSave() {
    if (lbAutoSaveTm) clearInterval(lbAutoSaveTm);
    lbAutoSaveTm = setInterval(function() {
      document.querySelectorAll('.lb-card[data-block-id]').forEach(function(card) {
        lbSaveBlock(+card.dataset.blockId);
      });
    }, 60000);
  }

  /* ── MCQ inline create ─────────────────────────────────────────────────── */

  function addMcqChoice(blockId) {
    var container = document.getElementById('new-mcq-choices-' + blockId);
    if (!container) return;
    var idx = mcqChoiceCount[blockId] = (mcqChoiceCount[blockId] || 2);
    var labels = ['A', 'B', 'C', 'D', 'E', 'F'];
    var row = document.createElement('div');
    row.className = 'flex items-center gap-2 mcq-choice-row';
    row.innerHTML = '<input type="radio" name="new-mcq-correct-' + blockId + '" value="' + idx + '" class="mcq-correct-radio flex-shrink-0">' +
      '<input type="text" placeholder="Choix ' + (labels[idx] || idx) + '" class="mcq-choice-text flex-1 px-2 py-1 border border-slate-300 rounded text-xs">' +
      '<button type="button" onclick="removeMcqChoice(this)" class="text-red-400 text-xs px-1">✕</button>';
    container.appendChild(row);
    mcqChoiceCount[blockId] = idx + 1;
  }

  function removeMcqChoice(btn) {
    var row = btn.closest('.mcq-choice-row');
    if (row) row.remove();
  }

  async function lbCreateMcqForBlock(blockId) {
    var title = document.getElementById('new-mcq-title-' + blockId)?.value.trim();
    var question = document.getElementById('new-mcq-q-' + blockId)?.value.trim();
    if (!title || !question) {
      if (window.nbToast) nbToast('Titre et question sont obligatoires.', 'error');
      return;
    }
    var choices = [];
    var container = document.getElementById('new-mcq-choices-' + blockId);
    if (container) {
      container.querySelectorAll('.mcq-choice-row').forEach(function(row, idx) {
        var text = row.querySelector('.mcq-choice-text')?.value.trim();
        var radio = row.querySelector('.mcq-correct-radio');
        if (text) choices.push({ text: text, is_correct: !!(radio && radio.checked), feedback: '', order: idx });
      });
    }
    if (choices.length < 2 || !choices.some(function(c) { return c.is_correct; })) {
      if (window.nbToast) nbToast('Au moins 2 choix et une bonne réponse requis.', 'error');
      return;
    }
    var r = await fetch('/fr/admin-panel/blocks/' + blockId + '/create-mcq/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({
        title: title,
        question: question,
        choices: choices,
        difficulty: document.getElementById('new-mcq-diff-' + blockId)?.value,
        points: document.getElementById('new-mcq-pts-' + blockId)?.value,
        max_attempts: document.getElementById('new-mcq-maxatt-' + blockId)?.value,
        explanation: document.getElementById('new-mcq-expl-' + blockId)?.value,
        hint: document.getElementById('new-mcq-hint-' + blockId)?.value,
        shuffle_choices: true,
      }),
    });
    var d = await r.json();
    if (d.success) {
      if (window.nbToast) nbToast('🔘 QCM «' + d.mcq_title + '» créé.', 'success');
      await lbSaveBlock(blockId);
    } else if (window.nbToast) {
      nbToast('Erreur: ' + (d.error || 'inconnue'), 'error');
    }
  }

  /* ── Code exercise inline create ───────────────────────────────────────── */

  async function lbRefreshLessonExercises(blockId, lessonId, lessonType) {
    var sel = document.getElementById('ex-sel-' + blockId);
    if (!sel) return;
    sel.innerHTML = '<option value="">Chargement…</option>';
    var url = lessonType === 'formation'
      ? '/fr/admin-panel/formation-lessons/' + lessonId + '/exercises/'
      : '/fr/admin-panel/lessons/' + lessonId + '/exercises/';
    var r = await fetch(url);
    var d = await r.json();
    sel.innerHTML = '<option value="">— Aucun exercice —</option>';
    (d.exercises || []).forEach(function(ex) {
      sel.add(new Option(ex.title + ' (' + ex.difficulty + ', ' + ex.points + ' pts)', ex.id));
    });
  }

  async function lbCreateExerciseForBlock(blockId, lessonId, lessonType) {
    var title = document.getElementById('new-ex-title-' + blockId)?.value.trim();
    var starter = document.getElementById('new-ex-starter-' + blockId)?.value;
    var solution = document.getElementById('new-ex-solution-' + blockId)?.value;
    if (!title || !starter || !solution) {
      if (window.nbToast) nbToast('Titre, code de départ et solution requis.', 'error');
      return;
    }
    var url = lessonType === 'formation'
      ? '/fr/admin-panel/formation-lessons/' + lessonId + '/blocks/' + blockId + '/create-exercise/'
      : '/fr/admin-panel/lessons/' + lessonId + '/blocks/' + blockId + '/create-exercise/';
    var r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({
        title: title,
        difficulty: document.getElementById('new-ex-diff-' + blockId)?.value,
        points: document.getElementById('new-ex-pts-' + blockId)?.value,
        evaluation_mode: document.getElementById('new-ex-mode-' + blockId)?.value,
        starter_code: starter,
        expected_output: document.getElementById('new-ex-expected-' + blockId)?.value,
        solution_code: solution,
      }),
    });
    var d = await r.json();
    if (d.success) {
      if (window.nbToast) nbToast('✅ Exercice «' + d.exercise_title + '» créé.', 'success');
      var sel = document.getElementById('ex-sel-' + blockId);
      if (sel) sel.add(new Option(d.exercise_title + ' (' + d.difficulty + ', ' + d.points + ' pts)', d.exercise_id, true, true));
      await lbSaveBlock(blockId);
    } else if (window.nbToast) {
      nbToast('Erreur lors de la création.', 'error');
    }
  }

  /* ── Export globals ────────────────────────────────────────────────────── */
  window.loadLessonBlocks = loadLessonBlocks;
  window.lbInitAll = lbInitAll;
  window.lbSaveBlock = lbSaveBlock;
  window.lbAddBlock = lbAddBlock;
  window.lbShowAddMenu = lbShowAddMenu;
  window.lbDeleteBlock = lbDeleteBlock;
  window.lbToggle = lbToggle;
  window.lbDragStart = lbDragStart;
  window.lbDragOver = lbDragOver;
  window.lbDragLeave = lbDragLeave;
  window.lbDrop = lbDrop;
  window.lbUpdatePreview = lbUpdatePreview;
  window.addMcqChoice = addMcqChoice;
  window.removeMcqChoice = removeMcqChoice;
  window.lbCreateMcqForBlock = lbCreateMcqForBlock;
  window.lbRefreshLessonExercises = lbRefreshLessonExercises;
  window.lbRefreshFormationExercises = function(bid, lid) { return lbRefreshLessonExercises(bid, lid, 'formation'); };
  window.lbCreateExerciseForBlock = lbCreateExerciseForBlock;
})();
