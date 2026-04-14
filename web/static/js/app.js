/**
 * ImageGenPro Web v2 - App-level interactions (Phase 3)
 */

(function () {
  /* ---------- Utilities ---------- */
  function padNum(n) {
    return n.toString().padStart(2, '0');
  }

  function escapeHtml(str) {
    return str.replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }

  function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2);
  }

  /* ---------- localStorage Data Layer ---------- */
  const LS_KEYS = {
    templates: 'igp_templates_v2',
    favorites: 'igp_favorites_v2',
    recent: 'igp_recent_templates_v2',
  };

  const BUILTIN_TEMPLATES = [
    { id: 'builtin_1', name: '电商白底图', content: '一款[产品]，简约设计，纹理清晰，纯白背景，专业产品摄影，柔和studio灯光，超高清细节', type: 'builtin' },
    { id: 'builtin_2', name: 'ins风场景', content: '一款[产品]，放在浅色木质桌面上，自然光从窗户洒入，绿植点缀，ins风格生活方式摄影', type: 'builtin' },
    { id: 'builtin_3', name: '街头时尚', content: '年轻亚洲女性模特手持[产品]，城市街道背景，时尚穿搭，自然光线，街拍风格', type: 'builtin' },
    { id: 'builtin_4', name: '咖啡厅氛围', content: '一款[产品]，放在咖啡厅大理石桌面上，拿铁咖啡旁边，暖色调灯光，慵懒午后氛围', type: 'builtin' },
    { id: 'builtin_5', name: '高级感光影', content: '一款[产品]，黑色背景，戏剧性侧光，产品轮廓光，高级奢侈品摄影风格', type: 'builtin' },
    { id: 'builtin_6', name: '模特手持图', content: '亚洲女性模特，穿着简约白色上衣，自然微笑，手持[产品]，纯白背景，专业电商人像摄影', type: 'builtin' },
  ];

  function lsGet(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  }

  function lsSet(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      // ignore
    }
  }

  function initData() {
    const existing = lsGet(LS_KEYS.templates, null);
    if (!existing || !Array.isArray(existing) || existing.length === 0) {
      lsSet(LS_KEYS.templates, BUILTIN_TEMPLATES);
    }
    if (!lsGet(LS_KEYS.favorites, null)) lsSet(LS_KEYS.favorites, []);
    if (!lsGet(LS_KEYS.recent, null)) lsSet(LS_KEYS.recent, []);
  }

  function getTemplates() {
    return lsGet(LS_KEYS.templates, []);
  }

  function setTemplates(list) {
    lsSet(LS_KEYS.templates, list);
  }

  function getFavorites() {
    return lsGet(LS_KEYS.favorites, []);
  }

  function setFavorites(list) {
    lsSet(LS_KEYS.favorites, list);
  }

  function getRecent() {
    return lsGet(LS_KEYS.recent, []);
  }

  function setRecent(list) {
    lsSet(LS_KEYS.recent, list.slice(0, 20));
  }

  function addRecent(templateId) {
    const recent = getRecent();
    const filtered = recent.filter((id) => id !== templateId);
    filtered.unshift(templateId);
    setRecent(filtered);
  }

  /* ---------- SPA View Switching ---------- */
  function initViewSwitching() {
    const navLinks = document.querySelectorAll('.nav-link');
    const views = {
      generate: document.getElementById('view-generate'),
      templates: document.getElementById('view-templates'),
      favorites: document.getElementById('view-favorites'),
    };

    function switchView(target) {
      Object.keys(views).forEach((key) => {
        const el = views[key];
        if (key === target) {
          el.classList.remove('hidden');
          // small delay to allow display change before opacity transition
          requestAnimationFrame(() => el.classList.add('active'));
        } else {
          el.classList.remove('active');
          setTimeout(() => el.classList.add('hidden'), 300);
        }
      });
      navLinks.forEach((link) => {
        if (link.getAttribute('data-view') === target) link.classList.add('active');
        else link.classList.remove('active');
      });
      if (target === 'templates') renderTemplateLibrary();
      if (target === 'favorites') renderFavorites();
    }

    navLinks.forEach((link) => {
      link.addEventListener('click', () => {
        const view = link.getAttribute('data-view');
        if (view) switchView(view);
      });
    });

    document.getElementById('nav-brand').addEventListener('click', () => switchView('generate'));

    window.switchAppView = switchView;
  }

  /* ---------- API Config ---------- */
  function initApiConfig() {
    const provider = document.getElementById('provider');
    const modelGroup = document.getElementById('model-group');
    const customModelGroup = document.getElementById('custom-model-group');
    const customUrlGroup = document.getElementById('custom-url-group');
    const modelSelect = document.getElementById('model');
    const customModelInput = document.getElementById('custom-model');
    const apiKeyInput = document.getElementById('api-key');
    const apiKeyToggle = document.getElementById('api-key-toggle');

    if (!provider) return;

    function updateApiUI() {
      const isCustom = provider.value === 'custom';
      if (isCustom) {
        modelGroup.classList.add('hidden');
        customModelGroup.classList.remove('hidden');
        customUrlGroup.classList.remove('hidden');
      } else {
        modelGroup.classList.remove('hidden');
        customModelGroup.classList.add('hidden');
        customUrlGroup.classList.add('hidden');
        if (modelSelect.value === 'custom') {
          customModelGroup.classList.remove('hidden');
        } else {
          customModelGroup.classList.add('hidden');
        }
      }
    }

    provider.addEventListener('change', updateApiUI);
    modelSelect.addEventListener('change', updateApiUI);

    apiKeyToggle.addEventListener('click', () => {
      const isPassword = apiKeyInput.type === 'password';
      apiKeyInput.type = isPassword ? 'text' : 'password';
      apiKeyToggle.textContent = isPassword ? '👈' : '👁';
      apiKeyToggle.setAttribute('aria-label', isPassword ? '隐藏密码' : '显示密码');
    });

    updateApiUI();
  }

  /* ---------- Aspect & Quality Pills ---------- */
  function initPillGroups() {
    function bindGroup(selector, dataAttr) {
      const groups = document.querySelectorAll(selector);
      groups.forEach((group) => {
        const buttons = group.querySelectorAll(`button[${dataAttr}]`);
        buttons.forEach((btn) => {
          btn.addEventListener('click', () => {
            buttons.forEach((b) => b.classList.remove('active'));
            btn.classList.add('active');
          });
        });
      });
    }
    bindGroup('[data-aspect-group]', 'data-aspect');
    bindGroup('[data-quality-group]', 'data-quality');
  }

  /* ---------- Reference Images ---------- */
  function initReferenceImages() {
    const zone = document.getElementById('ref-drop-zone');
    const input = document.getElementById('ref-file-input');
    const grid = document.getElementById('ref-thumb-grid');
    const copyBtn = document.getElementById('copy-ref-paths');

    if (!zone || !input || !grid) return;

    function renderThumbs() {
      grid.innerHTML = '';
      referenceImages.forEach((img, idx) => {
        const item = document.createElement('div');
        item.className = 'ref-thumb-item';
        item.innerHTML = `
          <img src="${escapeHtml(img.dataUrl)}" alt="${escapeHtml(img.name)}">
          <button class="ref-thumb-delete" data-idx="${idx}" aria-label="删除">×</button>
        `;
        grid.appendChild(item);
      });

      grid.querySelectorAll('.ref-thumb-delete').forEach((btn) => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const idx = parseInt(btn.getAttribute('data-idx'), 10);
          referenceImages.splice(idx, 1);
          renderThumbs();
        });
      });
    }

    function handleFiles(files) {
      Array.from(files).forEach((file) => {
        if (!file.type.startsWith('image/')) return;
        const reader = new FileReader();
        reader.onload = (e) => {
          referenceImages.push({ name: file.name, dataUrl: e.target.result });
          renderThumbs();
        };
        reader.readAsDataURL(file);
      });
    }

    zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      zone.style.borderColor = 'var(--color-accent)';
      zone.style.background = 'var(--hover-bg)';
    });

    zone.addEventListener('dragleave', () => {
      zone.style.borderColor = '';
      zone.style.background = '';
    });

    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.style.borderColor = '';
      zone.style.background = '';
      if (e.dataTransfer && e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
      }
    });

    zone.addEventListener('click', () => {
      input.click();
    });

    input.addEventListener('change', () => {
      if (input.files && input.files.length > 0) {
        handleFiles(input.files);
        input.value = '';
      }
    });

    copyBtn.addEventListener('click', async () => {
      if (refImages.length === 0) {
        alert('没有参考图可复制');
        return;
      }
      const text = referenceImages.map((img) => img.dataUrl).join('\n');
      try {
        await navigator.clipboard.writeText(text);
        const original = copyBtn.textContent;
        copyBtn.textContent = '✅ 已复制';
        setTimeout(() => (copyBtn.textContent = original), 1500);
      } catch (err) {
        console.error('Copy failed', err);
      }
    });
  }

  /* ---------- Prompt Cards ---------- */
  let promptCards = [];
  let nextCardId = 1;
  let referenceImages = [];

  function getPromptCardIndexById(id) {
    return promptCards.findIndex((c) => c.id === id);
  }

  function syncPromptCardData() {
    const list = document.getElementById('prompt-list');
    promptCards.forEach((card) => {
      const ta = list.querySelector(`textarea[data-prompt="${card.id}"]`);
      const inp = list.querySelector(`input[data-filename="${card.id}"]`);
      if (ta) card.prompt = ta.value;
      if (inp) card.filename = inp.value;
    });
  }

  function findFirstEmptyPromptCard() {
    return promptCards.find((c) => !c.prompt.trim());
  }

  function applyPromptToFirstEmpty(text) {
    syncPromptCardData();
    const card = findFirstEmptyPromptCard();
    if (card) {
      card.prompt = text;
      const list = document.getElementById('prompt-list');
      const ta = list.querySelector(`textarea[data-prompt="${card.id}"]`);
      if (ta) {
        ta.value = text;
        ta.dispatchEvent(new Event('input'));
      }
    } else {
      // if no empty, add new card
      const newCard = { id: nextCardId++, prompt: text, filename: '' };
      promptCards.push(newCard);
      renderPromptList();
      setTimeout(() => {
        const last = document.getElementById('prompt-list').lastElementChild;
        if (last) last.scrollIntoView({ behavior: 'smooth', block: 'end' });
      }, 0);
    }
  }

  function initPromptCards() {
    const list = document.getElementById('prompt-list');
    const addBtn = document.getElementById('add-prompt-card');
    const popup = document.getElementById('template-popup');
    const closePopup = document.getElementById('close-template-popup');

    let activeTemplateCardId = null;

    function createCardData() {
      return { id: nextCardId++, prompt: '', filename: '' };
    }

    function renumberCards() {
      const cards = list.querySelectorAll('.prompt-card');
      cards.forEach((card, idx) => {
        const indexEl = card.querySelector('.prompt-card-index');
        if (indexEl) indexEl.textContent = `#${padNum(idx + 1)}`;
      });
    }

    function buildCardHTML(card) {
      return `
        <div class="prompt-card-header">
          <span class="prompt-card-index">#${padNum(getPromptCardIndexById(card.id) + 1)}</span>
          <div class="prompt-card-actions">
            <button class="btn-icon btn-sm move-up-btn" data-id="${card.id}" title="上移">▲</button>
            <button class="btn-icon btn-sm delete-card-btn" data-id="${card.id}" title="删除">🗑️</button>
          </div>
        </div>
        <textarea class="form-textarea prompt-textarea" data-prompt="${card.id}" placeholder="例如：一位穿着未来风格外套的女性站在霓虹灯闪烁的东京街头，雨夜，电影感打光，8K 细节...">${escapeHtml(card.prompt)}</textarea>
        <div class="prompt-card-footer">
          <div class="filename-row">
            <span class="filename-label">文件名:</span>
            <input type="text" class="form-input filename-input" data-filename="${card.id}" value="${escapeHtml(card.filename)}" placeholder="image_01">
            <button class="btn btn-secondary btn-sm auto-name-btn" data-id="${card.id}">🎲 自动命名</button>
          </div>
          <div class="template-status-row">
            <div style="display:flex;gap:8px;">
              <button class="btn btn-secondary btn-sm insert-template-btn" data-id="${card.id}">📋 插入模板</button>
              <button class="btn btn-secondary btn-sm save-favorite-btn" data-id="${card.id}">♡ 保存收藏</button>
            </div>
            <span class="status-text"><span class="status-dot waiting"></span> 等待中</span>
          </div>
        </div>
      `;
    }

    window.renderPromptList = function renderPromptList() {
      list.innerHTML = '';
      promptCards.forEach((card) => {
        const el = document.createElement('div');
        el.className = 'prompt-card';
        el.setAttribute('data-card-id', card.id);
        el.innerHTML = buildCardHTML(card);
        list.appendChild(el);
      });
      renumberCards();
      bindCardEvents();
    };

    function bindCardEvents() {
      list.querySelectorAll('.delete-card-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          const id = parseInt(btn.getAttribute('data-id'), 10);
          const idx = getPromptCardIndexById(id);
          if (idx > -1) {
            syncPromptCardData();
            promptCards.splice(idx, 1);
            renderPromptList();
          }
        });
      });

      list.querySelectorAll('.move-up-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          const id = parseInt(btn.getAttribute('data-id'), 10);
          const idx = getPromptCardIndexById(id);
          if (idx > 0) {
            syncPromptCardData();
            const temp = promptCards[idx];
            promptCards[idx] = promptCards[idx - 1];
            promptCards[idx - 1] = temp;
            renderPromptList();
          }
        });
      });

      list.querySelectorAll('.auto-name-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          const id = parseInt(btn.getAttribute('data-id'), 10);
          const textarea = list.querySelector(`textarea[data-prompt="${id}"]`);
          const input = list.querySelector(`input[data-filename="${id}"]`);
          const promptText = textarea ? textarea.value.trim() : '';
          let name = 'image';
          if (promptText) {
            const cleaned = promptText.replace(/[，,。！!？?;;：]/g, ' ');
            const words = cleaned.trim().split(/\s+/).filter((w) => w.length > 0);
            if (words.length >= 2) {
              name = words.slice(0, 2).join('_');
            } else if (words.length === 1) {
              name = words[0];
            }
          }
          const idx = getPromptCardIndexById(id) + 1;
          input.value = `${name}_${padNum(idx)}`;
          syncPromptCardData();
        });
      });

      list.querySelectorAll('.insert-template-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          activeTemplateCardId = parseInt(btn.getAttribute('data-id'), 10);
          renderTemplatePopupGrid();
          popup.classList.remove('hidden');
        });
      });

      list.querySelectorAll('.save-favorite-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          const id = parseInt(btn.getAttribute('data-id'), 10);
          const ta = list.querySelector(`textarea[data-prompt="${id}"]`);
          const text = ta ? ta.value.trim() : '';
          if (!text) {
            alert('提示词为空，无法保存');
            return;
          }
          openSaveFavoriteModal(text);
        });
      });

      list.querySelectorAll('textarea[data-prompt]').forEach((ta) => {
        ta.addEventListener('input', syncPromptCardData);
      });

      list.querySelectorAll('input[data-filename]').forEach((inp) => {
        inp.addEventListener('input', syncPromptCardData);
      });
    }

    // Initialize with 8 cards
    for (let i = 0; i < 8; i++) {
      promptCards.push(createCardData());
    }
    renderPromptList();

    addBtn.addEventListener('click', () => {
      syncPromptCardData();
      promptCards.push(createCardData());
      renderPromptList();
      setTimeout(() => {
        const last = list.lastElementChild;
        if (last) last.scrollIntoView({ behavior: 'smooth', block: 'end' });
      }, 0);
    });

    closePopup.addEventListener('click', () => {
      popup.classList.add('hidden');
      activeTemplateCardId = null;
    });

    popup.addEventListener('click', (e) => {
      if (e.target === popup) {
        popup.classList.add('hidden');
        activeTemplateCardId = null;
      }
    });
  }

  function renderTemplatePopupGrid() {
    const grid = document.getElementById('template-popup-grid');
    const templates = getTemplates().filter((t) => t.type === 'builtin' || t.type === 'custom');
    grid.innerHTML = templates.map((t) => `
      <button class="template-item" data-template-id="${escapeHtml(t.id)}">${escapeHtml(t.name)}</button>
    `).join('');

    grid.querySelectorAll('.template-item').forEach((item) => {
      item.addEventListener('click', () => {
        const id = item.getAttribute('data-template-id');
        const tpl = getTemplates().find((t) => t.id === id);
        if (!tpl) return;
        const popup = document.getElementById('template-popup');
        // find active card from popup context
        // We need to know which card opened the popup. The original implementation uses activeTemplateCardId
        // but it's local to initPromptCards. We'll use a global variable set by the popup opener.
        const cardId = window._activeTemplateCardId;
        if (cardId != null) {
          const list = document.getElementById('prompt-list');
          const ta = list.querySelector(`textarea[data-prompt="${cardId}"]`);
          if (ta) {
            const text = tpl.content || '';
            if (ta.value && !ta.value.endsWith('\n') && ta.value.length > 0) {
              ta.value += '\n' + text;
            } else {
              ta.value += text;
            }
            ta.dispatchEvent(new Event('input'));
          }
        }
        popup.classList.add('hidden');
        window._activeTemplateCardId = null;
      });
    });
  }

  // Hook the insert-template-btn to set global active id
  const originalInitPromptCards = initPromptCards;
  initPromptCards = function() {
    originalInitPromptCards();
    const list = document.getElementById('prompt-list');
    list.addEventListener('click', (e) => {
      const btn = e.target.closest('.insert-template-btn');
      if (btn) {
        window._activeTemplateCardId = parseInt(btn.getAttribute('data-id'), 10);
      }
    });
  };

  /* ---------- Output Directory Browse ---------- */
  function initBrowseButton() {
    const browseBtn = document.getElementById('browse-output-dir');
    const browseInput = document.getElementById('browse-dir-input');
    const outputDir = document.getElementById('output-dir');

    if (!browseBtn || !browseInput || !outputDir) return;

    browseBtn.addEventListener('click', () => {
      browseInput.click();
    });

    browseInput.addEventListener('change', () => {
      if (browseInput.files && browseInput.files.length > 0) {
        const first = browseInput.files[0];
        const path = first.webkitRelativePath;
        if (path) {
          const dirName = path.split('/')[0];
          outputDir.value = '/mnt/e/Outputs/ImageGenPro/' + dirName;
        }
      }
    });
  }

  /* ---------- Right Panel Preview ---------- */
  const previewState = {
    isGenerating: false,
    currentTask: null,
    progress: 0,
    eta: 0,
    thumbnails: [], // {id, url, status: 'success'|'failed'}
    tab: 'all', // all | success | failed
  };

  function initPreviewPanel() {
    const tabs = document.querySelectorAll('#preview-tabs .preview-tab');
    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        tabs.forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        previewState.tab = tab.getAttribute('data-tab');
        renderThumbnails();
      });
    });
  }

  function setPreviewGenerating(taskName) {
    previewState.isGenerating = true;
    previewState.currentTask = taskName;
    previewState.progress = 0;

    document.getElementById('preview-subtitle').textContent = `正在生成 ${taskName}`;
    document.getElementById('preview-badge').textContent = '生成中';
    document.getElementById('preview-badge').className = 'badge badge-warning';
    document.getElementById('preview-placeholder').classList.add('hidden');
    document.getElementById('preview-image').classList.add('hidden');
    document.getElementById('preview-loading').classList.remove('hidden');
    document.getElementById('preview-progress-wrap').classList.remove('hidden');
    document.getElementById('preview-status').textContent = '生成中...';
  }

  function setPreviewIdle() {
    previewState.isGenerating = false;
    previewState.currentTask = null;
    document.getElementById('preview-subtitle').textContent = '生成结果将在此显示';
    document.getElementById('preview-badge').textContent = '就绪';
    document.getElementById('preview-badge').className = 'badge badge-success';
    document.getElementById('preview-placeholder').classList.remove('hidden');
    document.getElementById('preview-image').classList.add('hidden');
    document.getElementById('preview-loading').classList.add('hidden');
    document.getElementById('preview-progress-wrap').classList.add('hidden');
    document.getElementById('preview-status').textContent = '等待生成';
  }

  function setPreviewProgress(pct, etaSec) {
    previewState.progress = pct;
    previewState.eta = etaSec;
    const bar = document.getElementById('preview-progress-bar');
    bar.style.width = pct + '%';
    const etaText = etaSec > 0 ? ` 预估剩余 ${Math.ceil(etaSec)}秒` : '';
    document.getElementById('preview-status').textContent = `生成中...${pct}%${etaText}`;
  }

  function addThumbnail(url, status, error) {
    previewState.thumbnails.push({ id: generateId(), url, status, error: error || '' });
    renderThumbnails();
  }

  function renderThumbnails() {
    const container = document.getElementById('preview-thumbnails');
    const filtered = previewState.thumbnails.filter((t) => {
      if (previewState.tab === 'all') return true;
      return t.status === previewState.tab;
    });

    if (filtered.length === 0) {
      container.innerHTML = `<div class="thumb-empty">暂无生成记录</div>`;
      return;
    }

    container.innerHTML = filtered.map((t) => {
      const imgHtml = t.url
        ? `<img src="${escapeHtml(t.url)}" alt="thumb">`
        : `<div class="thumb-placeholder-failed"><span>❌</span><small>生成失败</small></div>`;
      return `
      <div class="thumb-card ${t.status === 'failed' ? 'thumb-failed' : ''}" data-thumb-id="${escapeHtml(t.id)}">
        ${imgHtml}
        ${t.status === 'failed' ? '<div class="thumb-failed-badge">✕</div>' : ''}
        <div class="thumb-menu">
          <button class="thumb-menu-btn" data-action="folder">打开文件夹</button>
          ${t.status === 'failed' ? `<button class="thumb-menu-btn" data-action="retry">重试</button>` : ''}
          <button class="thumb-menu-btn" data-action="delete">删除</button>
        </div>
      </div>
    `;
    }).join('');

    container.querySelectorAll('.thumb-card').forEach((card) => {
      const id = card.getAttribute('data-thumb-id');
      card.querySelectorAll('.thumb-menu-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const action = btn.getAttribute('data-action');
          if (action === 'delete') {
            previewState.thumbnails = previewState.thumbnails.filter((x) => x.id !== id);
            renderThumbnails();
          } else if (action === 'retry') {
            alert('重试功能需在后续版本实现');
          } else if (action === 'folder') {
            alert('打开文件夹功能需在后续版本实现');
          }
        });
      });
    });
  }

  /* ---------- Template Library ---------- */
  let currentTemplateFilter = 'all';

  function initTemplateLibrary() {
    const tabs = document.querySelectorAll('#template-tabs .template-tab');
    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        tabs.forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        currentTemplateFilter = tab.getAttribute('data-filter');
        renderTemplateLibrary();
      });
    });

    document.getElementById('btn-new-template').addEventListener('click', () => {
      openNewTemplateModal();
    });

    // New template modal
    document.getElementById('close-new-template-modal').addEventListener('click', closeNewTemplateModal);
    document.getElementById('cancel-new-template').addEventListener('click', closeNewTemplateModal);
    document.getElementById('save-new-template').addEventListener('click', () => {
      const name = document.getElementById('new-template-name').value.trim();
      const content = document.getElementById('new-template-content').value.trim();
      if (!name || !content) {
        alert('请填写模板名称和内容');
        return;
      }
      const list = getTemplates();
      list.push({ id: generateId(), name, content, type: 'custom' });
      setTemplates(list);
      closeNewTemplateModal();
      renderTemplateLibrary();
    });

    document.getElementById('new-template-modal').addEventListener('click', (e) => {
      if (e.target.id === 'new-template-modal') closeNewTemplateModal();
    });

    // Product input modal
    document.getElementById('close-product-input-modal').addEventListener('click', closeProductInputModal);
    document.getElementById('cancel-product-input').addEventListener('click', closeProductInputModal);
    document.getElementById('confirm-product-input').addEventListener('click', () => {
      const val = document.getElementById('product-input-value').value.trim();
      const tpl = window._pendingProductTemplate;
      if (tpl) {
        const text = tpl.content.replace(/\[产品\]/g, val || '产品');
        addRecent(tpl.id);
        window.switchAppView('generate');
        applyPromptToFirstEmpty(text);
      }
      closeProductInputModal();
    });
    document.getElementById('product-input-modal').addEventListener('click', (e) => {
      if (e.target.id === 'product-input-modal') closeProductInputModal();
    });
  }

  function openNewTemplateModal() {
    document.getElementById('new-template-name').value = '';
    document.getElementById('new-template-content').value = '';
    document.getElementById('new-template-modal').classList.remove('hidden');
  }

  function closeNewTemplateModal() {
    document.getElementById('new-template-modal').classList.add('hidden');
  }

  function openProductInputModal(template) {
    window._pendingProductTemplate = template;
    document.getElementById('product-input-value').value = '';
    document.getElementById('product-input-modal').classList.remove('hidden');
  }

  function closeProductInputModal() {
    document.getElementById('product-input-modal').classList.add('hidden');
    window._pendingProductTemplate = null;
  }

  function renderTemplateLibrary() {
    const grid = document.getElementById('template-grid-page');
    const all = getTemplates();
    const recentIds = getRecent();

    let displayList = [];
    if (currentTemplateFilter === 'all') {
      displayList = all;
    } else if (currentTemplateFilter === 'builtin') {
      displayList = all.filter((t) => t.type === 'builtin');
    } else if (currentTemplateFilter === 'custom') {
      displayList = all.filter((t) => t.type === 'custom');
    } else if (currentTemplateFilter === 'recent') {
      const map = new Map(all.map((t) => [t.id, t]));
      displayList = recentIds.map((id) => map.get(id)).filter(Boolean);
    }

    if (displayList.length === 0) {
      grid.innerHTML = `<div class="empty-state">暂无模板</div>`;
      return;
    }

    grid.innerHTML = displayList.map((t) => {
      const isCustom = t.type === 'custom';
      return `
        <div class="template-card-page">
          <div class="template-card-header">
            <div class="template-card-name">${escapeHtml(t.name)}</div>
            <span class="template-card-tag ${t.type}">${t.type === 'builtin' ? '内置' : t.type === 'custom' ? '自定义' : ''}</span>
          </div>
          <div class="template-card-content">${escapeHtml(t.content)}</div>
          <div class="template-card-actions">
            <button class="btn btn-primary btn-sm use-template-btn" data-id="${escapeHtml(t.id)}">使用</button>
            ${isCustom ? `<button class="btn btn-secondary btn-sm edit-template-btn" data-id="${escapeHtml(t.id)}">编辑</button>` : ''}
            ${isCustom ? `<button class="btn btn-secondary btn-sm delete-template-btn" data-id="${escapeHtml(t.id)}">删除</button>` : ''}
          </div>
        </div>
      `;
    }).join('');

    grid.querySelectorAll('.use-template-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        const tpl = all.find((t) => t.id === id);
        if (!tpl) return;
        if (tpl.content.includes('[产品]')) {
          openProductInputModal(tpl);
        } else {
          addRecent(tpl.id);
          window.switchAppView('generate');
          applyPromptToFirstEmpty(tpl.content);
        }
      });
    });

    grid.querySelectorAll('.delete-template-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        if (!confirm('确定删除该模板？')) return;
        setTemplates(all.filter((t) => t.id !== id));
        renderTemplateLibrary();
      });
    });

    grid.querySelectorAll('.edit-template-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        const tpl = all.find((t) => t.id === id);
        if (!tpl) return;
        const newName = prompt('模板名称', tpl.name);
        if (newName === null) return;
        const newContent = prompt('模板内容', tpl.content);
        if (newContent === null) return;
        tpl.name = newName.trim() || tpl.name;
        tpl.content = newContent.trim() || tpl.content;
        setTemplates(all);
        renderTemplateLibrary();
      });
    });
  }

  /* ---------- Favorites ---------- */
  function initFavorites() {
    const search = document.getElementById('favorites-search');
    search.addEventListener('input', () => {
      renderFavorites(search.value.trim());
    });

    // Save favorite modal
    document.getElementById('close-save-favorite-modal').addEventListener('click', closeSaveFavoriteModal);
    document.getElementById('cancel-save-favorite').addEventListener('click', closeSaveFavoriteModal);
    document.getElementById('confirm-save-favorite').addEventListener('click', () => {
      const name = document.getElementById('save-favorite-name').value.trim();
      const content = document.getElementById('save-favorite-content').value.trim();
      if (!name || !content) {
        alert('请填写名称和内容');
        return;
      }
      const list = getFavorites();
      list.push({ id: generateId(), name, content, createdAt: Date.now() });
      setFavorites(list);
      closeSaveFavoriteModal();
      if (!document.getElementById('view-favorites').classList.contains('hidden')) {
        renderFavorites();
      }
    });
    document.getElementById('save-favorite-modal').addEventListener('click', (e) => {
      if (e.target.id === 'save-favorite-modal') closeSaveFavoriteModal();
    });
  }

  function openSaveFavoriteModal(text) {
    const defaultName = text.replace(/[\n\r]/g, ' ').trim().split(/\s+/).slice(0, 2).join(' ');
    document.getElementById('save-favorite-name').value = defaultName;
    document.getElementById('save-favorite-content').value = text;
    document.getElementById('save-favorite-modal').classList.remove('hidden');
  }

  function closeSaveFavoriteModal() {
    document.getElementById('save-favorite-modal').classList.add('hidden');
  }

  function renderFavorites(query) {
    const container = document.getElementById('favorites-list');
    let list = getFavorites();
    if (query) {
      const q = query.toLowerCase();
      list = list.filter((f) => f.name.toLowerCase().includes(q) || f.content.toLowerCase().includes(q));
    }

    if (list.length === 0) {
      container.innerHTML = `<div class="empty-state">暂无收藏</div>`;
      return;
    }

    container.innerHTML = list.map((f) => `
      <div class="favorite-card">
        <div class="favorite-card-header">
          <div class="favorite-card-name">${escapeHtml(f.name)}</div>
          <div class="favorite-card-actions">
            <button class="btn btn-primary btn-sm apply-favorite-btn" data-id="${escapeHtml(f.id)}">应用到任务</button>
            <button class="btn btn-secondary btn-sm edit-favorite-btn" data-id="${escapeHtml(f.id)}">编辑</button>
            <button class="btn btn-secondary btn-sm delete-favorite-btn" data-id="${escapeHtml(f.id)}">删除</button>
          </div>
        </div>
        <div class="favorite-card-content">${escapeHtml(f.content)}</div>
      </div>
    `).join('');

    container.querySelectorAll('.apply-favorite-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        const fav = getFavorites().find((f) => f.id === id);
        if (fav) {
          window.switchAppView('generate');
          applyPromptToFirstEmpty(fav.content);
        }
      });
    });

    container.querySelectorAll('.edit-favorite-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        const fav = getFavorites().find((f) => f.id === id);
        if (!fav) return;
        const newName = prompt('收藏名称', fav.name);
        if (newName === null) return;
        const newContent = prompt('提示词内容', fav.content);
        if (newContent === null) return;
        fav.name = newName.trim() || fav.name;
        fav.content = newContent.trim() || fav.content;
        setFavorites(getFavorites());
        renderFavorites(document.getElementById('favorites-search').value.trim());
      });
    });

    container.querySelectorAll('.delete-favorite-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        if (!confirm('确定删除该收藏？')) return;
        setFavorites(getFavorites().filter((f) => f.id !== id));
        renderFavorites(document.getElementById('favorites-search').value.trim());
      });
    });
  }

  /* ---------- Health Check ---------- */
  function initHealthCheck() {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => {
        console.log('Health check:', data);
      })
      .catch((err) => {
        console.warn('Health check failed:', err);
      });
  }

  /* ---------- Batch Generate Real API ---------- */
  function initBatchGenerate() {
    const btn = document.getElementById('start-batch');
    if (!btn) return;
    btn.addEventListener('click', () => {
      if (previewState.isGenerating) return;
      syncPromptCardData();
      const tasks = promptCards.filter((c) => c.prompt.trim()).map((c, idx) => ({ ...c, idx }));
      if (tasks.length === 0) {
        alert('请至少填写一个提示词');
        return;
      }
      runRealGeneration(tasks);
    });
  }

  async function runRealGeneration(tasks) {
    const provider = document.getElementById('provider').value;
    const modelSelect = document.getElementById('model').value;
    const customModel = document.getElementById('custom-model').value.trim();
    const apiKey = document.getElementById('api-key').value.trim();
    const outputDir = document.getElementById('output-dir').value.trim();

    if (!apiKey) {
      alert('请填写 API 密钥');
      return;
    }
    if (!outputDir) {
      alert('请选择输出目录');
      return;
    }

    const config = {
      api_key: apiKey,
      api_url: provider === 'custom'
        ? (document.getElementById('custom-url').value.trim() || 'https://api.example.com/v1')
        : 'https://lnapi.com/v1beta/models/gemini-3-pro-image-preview:generateContent',
      model: provider === 'custom' ? (customModel || 'custom-model') : modelSelect,
      aspect_ratio: document.querySelector('.pill-group[data-aspect-group] .btn-pill.active')?.getAttribute('data-aspect') || '1:1',
      quality: document.querySelector('.pill-group[data-quality-group] .btn-pill.active')?.getAttribute('data-quality') || '2k',
      output_dir: outputDir,
    };

    const payload = {
      tasks: tasks.map((t) => ({
        id: t.id || padNum(t.idx + 1),
        prompt: t.prompt,
        filename: t.filename || `image_${padNum(t.idx + 1)}`,
      })),
      config,
      reference_images: referenceImages.map((img) => img.dataUrl),
    };

    setPreviewGenerating(`批量生成 ${tasks.length} 张图片`);
    setPreviewProgress(5, 0);

    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`服务器错误 ${res.status}: ${errText}`);
      }

      const results = await res.json();
      let successCount = 0;
      let failCount = 0;
      let skipCount = 0;

      results.forEach((r) => {
        if (r.skipped) {
          skipCount++;
          addThumbnail(`/api/image?path=${encodeURIComponent(config.output_dir + '/' + r.filename)}`, 'success');
        } else if (r.success) {
          successCount++;
          addThumbnail(`/api/image?path=${encodeURIComponent(config.output_dir + '/' + r.filename)}`, 'success');
        } else {
          failCount++;
          addThumbnail('', 'failed', r.error);
        }
      });

      setPreviewIdle();
      showGenerateModal(successCount, failCount, skipCount);
    } catch (err) {
      console.error(err);
      setPreviewIdle();
      alert('生成失败: ' + err.message);
    }
  }

  function showGenerateModal(success, fail, skip) {
    document.getElementById('modal-success-count').textContent = success;
    document.getElementById('modal-fail-count').textContent = fail;
    document.getElementById('modal-skip-count').textContent = skip;
    document.getElementById('modal-time').textContent = '刚刚完成';
    document.getElementById('generate-modal').classList.remove('hidden');
  }

  function closeGenerateModal() {
    document.getElementById('generate-modal').classList.add('hidden');
  }

  document.getElementById('close-generate-modal').addEventListener('click', closeGenerateModal);
  document.getElementById('generate-modal').addEventListener('click', (e) => {
    if (e.target.id === 'generate-modal') closeGenerateModal();
  });

  /* ---------- Init ---------- */
  function init() {
    initData();
    initViewSwitching();
    initApiConfig();
    initPillGroups();
    initReferenceImages();
    initPromptCards();
    initBrowseButton();
    initPreviewPanel();
    initTemplateLibrary();
    initFavorites();
    initBatchGenerate();
    initHealthCheck();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
