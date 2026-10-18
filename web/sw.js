/* Service worker: permite instalar la app y abre la interfaz aunque la red falle un momento.
   Solo guarda en caché los archivos de la interfaz; NUNCA los datos de estudiantes (/api, /datos). */
const VERSION = 'vocacional-v1';
const ARCHIVOS = ['/entrar', '/chaside', '/estilo.css', '/app.js', '/gestion.js', '/motor.js', '/figuras.js', '/chaside.js', '/entrar.js',
  '/icono.svg', '/icono-192.png', '/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(ARCHIVOS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/datos/') || url.pathname === '/') return;  // datos: siempre de la red
  // red primero (para recibir actualizaciones); si no hay conexión, la copia guardada
  e.respondWith(fetch(e.request).then(r => {
    if (r.ok) { const copia = r.clone(); caches.open(VERSION).then(c => c.put(e.request, copia)); }
    return r;
  }).catch(() => caches.match(e.request)));
});
