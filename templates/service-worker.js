const CACHE_NAME = 'luna-cliente-v1';
const urlsToCache = [
  '/',
  '/manifest.json',
  '/service-worker.js'
];

self.addEventListener('install', event => {
  console.log('✅ Cliente SW instalado');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
      .catch(err => console.log('⚠️ Error cacheando:', err))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  console.log('✅ Cliente SW activado');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('️ Eliminando cache viejo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if (!event.request.url.startsWith('http')) return;
  
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) return response;
        return fetch(event.request);
      })
      .catch(() => {
        return new Response('Offline - Sin conexión', {
          headers: { 'Content-Type': 'text/plain' }
        });
      })
  );
});