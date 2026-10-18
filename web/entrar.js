(() => {
  'use strict';
  const f = document.getElementById('f'), err = document.getElementById('err'), b = document.getElementById('b');
  f.addEventListener('submit', async e => {
    e.preventDefault();
    err.hidden = true; b.disabled = true; b.textContent = 'Entrando…';
    try {
      const r = await fetch('/api/sesion', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-Vocacional': '1' },
        body: JSON.stringify({ usuario: f.usuario.value.trim(), clave: f.clave.value })
      });
      if (r.ok) { location.href = '/'; return; }
      const d = await r.json().catch(() => ({}));
      err.textContent = d.error || 'No se pudo iniciar sesión.'; err.hidden = false;
    } catch (_) {
      err.textContent = 'Sin conexión con el servidor.'; err.hidden = false;
    }
    b.disabled = false; b.textContent = 'Entrar'; f.clave.select();
  });
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
})();
