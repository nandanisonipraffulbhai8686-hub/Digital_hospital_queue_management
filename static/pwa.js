// Ever Well PWA — Register Service Worker + Install Prompt
(function() {
  // Register service worker
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
      navigator.serviceWorker.register('/sw.js', { scope: '/' })
        .then(function(reg) {
          console.log('SW registered:', reg.scope);
        })
        .catch(function(err) {
          console.log('SW registration failed:', err);
        });
    });
  }

  // Install prompt
  var deferredPrompt = null;
  var installBtn = document.getElementById('pwaInstallBtn');

  window.addEventListener('beforeinstallprompt', function(e) {
    e.preventDefault();
    deferredPrompt = e;
    if (installBtn) {
      installBtn.style.display = 'flex';
    }
  });

  window.addEventListener('appinstalled', function() {
    deferredPrompt = null;
    if (installBtn) installBtn.style.display = 'none';
  });

  // Expose install function globally
  window.installPWA = function() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then(function(result) {
      deferredPrompt = null;
      if (installBtn) installBtn.style.display = 'none';
    });
  };
})();
