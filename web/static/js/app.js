/**
 * ImageGenPro Web v2 - App-level interactions
 */

(function () {
  function initAspectRatioButtons() {
    const groups = document.querySelectorAll('[data-aspect-group]');
    groups.forEach((group) => {
      const buttons = group.querySelectorAll('button[data-aspect]');
      buttons.forEach((btn) => {
        btn.addEventListener('click', () => {
          buttons.forEach((b) => b.classList.remove('active'));
          btn.classList.add('active');
        });
      });
    });
  }

  function initDropZones() {
    const zones = document.querySelectorAll('[data-drop-zone]');
    zones.forEach((zone) => {
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
          console.log('Dropped files:', e.dataTransfer.files);
        }
      });

      zone.addEventListener('click', () => {
        const input = zone.querySelector('input[type="file"]');
        if (input) input.click();
      });
    });
  }

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

  function init() {
    initAspectRatioButtons();
    initDropZones();
    initHealthCheck();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
