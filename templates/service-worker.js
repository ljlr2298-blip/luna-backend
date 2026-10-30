const CACHE_NAME = 'luna-pwa-v3';

self.addEventListener('install', event => {
  console.log('✅ SW instalado');
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  console.log('✅ SW activado');
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
        return new Response('Offline', {
          headers: { 'Content-Type': 'text/plain' }
        });
      })
  );
});