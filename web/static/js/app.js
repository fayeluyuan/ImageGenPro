/**
 * ImageGenPro Web v2 - App-level interactions
 */

(function () {
  /* ---------- Utilities ---------- */
  function padNum(n) {
    return n.toString().padStart(2, '0');
  }

  function escapeHtml(str) {
    return str.replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
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
      apiKeyToggle.textContent = isPassword ? '🙈' : '👁';
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

    const refImages = []; // { name, url }

    function renderThumbs() {
      grid.innerHTML = '';
      refImages.forEach((img, idx) => {
        const item = document.createElement('div');
        item.className = 'ref-thumb-item';
        item.innerHTML = `
          <img src="${escapeHtml(img.url)}" alt="${escapeHtml(img.name)}">
          <button class="ref-thumb-delete" data-idx="${idx}" aria-label="删除">×</button>
        `;
        grid.appendChild(item);
      });

      grid.querySelectorAll('.ref-thumb-delete').forEach((btn) => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const idx = parseInt(btn.getAttribute('data-idx'), 10);
          refImages.splice(idx, 1);
          renderThumbs();
        });
      });
    }

    function handleFiles(files) {
      Array.from(files).forEach((file) => {
        if (!file.type.startsWith('image/')) return;
        const url = URL.createObjectURL(file);
        refImages.push({ name: file.name, url });
      });
      renderThumbs();
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
      const text = refImages.map((img) => img.url).join('\n');
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
  function initPromptCards() {
    const list = document.getElementById('prompt-list');
    const addBtn = document.getElementById('add-prompt-card');
    const popup = document.getElementById('template-popup');
    const closePopup = document.getElementById('close-template-popup');
    const templateItems = popup.querySelectorAll('.template-item');

    let promptCards = [];
    let nextId = 1;
    let activeTemplateCardId = null;

    const templates = {
      '电商白底图': '白色纯色背景，商品展示，柔和影子，高端电商风格，细节清晰',
      'ins风场景': '温馨自然光，简约室内场景，低饱和色调，舒适懒人氛围',
      '街头时尚': '都市街头背景，时尚穿搭，自然动态，街拍感，高级灰调',
      '咖啡厅氛围': '咖啡厅内景，暖色调灯光，木质桌面，轻松惬意，生活美学',
      '高级感光影': '戏剧性光影，高对比度，精致质感，艺术摄影风格，细节丰富',
      '模特手持图': '模特手持产品，自然表情，柔和光线，专业商业摄影',
    };

    function createCardData() {
      return { id: nextId++, prompt: '', filename: '' };
    }

    function getCardIndexById(id) {
      return promptCards.findIndex((c) => c.id === id);
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
          <span class="prompt-card-index">#${padNum(getCardIndexById(card.id) + 1)}</span>
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
            <button class="btn btn-secondary btn-sm insert-template-btn" data-id="${card.id}">📋 插入模板</button>
            <span class="status-text"><span class="status-dot waiting"></span> 等待中</span>
          </div>
        </div>
      `;
    }

    function renderList() {
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
    }

    function bindCardEvents() {
      list.querySelectorAll('.delete-card-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          const id = parseInt(btn.getAttribute('data-id'), 10);
          const idx = getCardIndexById(id);
          if (idx > -1) {
            promptCards.splice(idx, 1);
            renderList();
          }
        });
      });

      list.querySelectorAll('.move-up-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          const id = parseInt(btn.getAttribute('data-id'), 10);
          const idx = getCardIndexById(id);
          if (idx > 0) {
            syncCardData();
            const temp = promptCards[idx];
            promptCards[idx] = promptCards[idx - 1];
            promptCards[idx - 1] = temp;
            renderList();
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
            // extract first two nouns-ish words (simple heuristic: first two segments separated by punctuation)
            const cleaned = promptText.replace(/[，,。.！!？?;；:\uff1a]/g, ' ');
            const words = cleaned.trim().split(/\s+/).filter((w) => w.length > 0);
            if (words.length >= 2) {
              name = words.slice(0, 2).join('_');
            } else if (words.length === 1) {
              name = words[0];
            }
          } else {
            name = 'image';
          }
          const idx = getCardIndexById(id) + 1;
          input.value = `${name}_${padNum(idx)}`;
          syncCardData();
        });
      });

      list.querySelectorAll('.insert-template-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          activeTemplateCardId = parseInt(btn.getAttribute('data-id'), 10);
          popup.classList.remove('hidden');
        });
      });

      list.querySelectorAll('textarea[data-prompt]').forEach((ta) => {
        ta.addEventListener('input', syncCardData);
      });

      list.querySelectorAll('input[data-filename]').forEach((inp) => {
        inp.addEventListener('input', syncCardData);
      });
    }

    function syncCardData() {
      promptCards.forEach((card) => {
        const ta = list.querySelector(`textarea[data-prompt="${card.id}"]`);
        const inp = list.querySelector(`input[data-filename="${card.id}"]`);
        if (ta) card.prompt = ta.value;
        if (inp) card.filename = inp.value;
      });
    }

    // Initialize with 8 cards
    for (let i = 0; i < 8; i++) {
      promptCards.push(createCardData());
    }
    renderList();

    addBtn.addEventListener('click', () => {
      syncCardData();
      promptCards.push(createCardData());
      renderList();
      // scroll to bottom
      setTimeout(() => {
        const last = list.lastElementChild;
        if (last) last.scrollIntoView({ behavior: 'smooth', block: 'end' });
      }, 0);
    });

    // Template popup
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

    templateItems.forEach((item) => {
      item.addEventListener('click', () => {
        const key = item.getAttribute('data-template');
        const text = templates[key] || '';
        if (activeTemplateCardId != null) {
          const ta = list.querySelector(`textarea[data-prompt="${activeTemplateCardId}"]`);
          if (ta) {
            if (ta.value && !ta.value.endsWith('\n') && ta.value.length > 0) {
              ta.value += '\n' + text;
            } else {
              ta.value += text;
            }
            ta.dispatchEvent(new Event('input'));
          }
        }
        popup.classList.add('hidden');
        activeTemplateCardId = null;
      });
    });
  }

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
      // webkitdirectory returns files; we take the first file's webkitRelativePath to guess dir
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

  /* ---------- Init ---------- */
  function init() {
    initApiConfig();
    initPillGroups();
    initReferenceImages();
    initPromptCards();
    initBrowseButton();
    initHealthCheck();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
