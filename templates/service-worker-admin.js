// Service Worker para notificaciones push (Modo Admin)
const CACHE_NAME = 'luna-admin-v1';
const urlsToCache = [
  '/',
  '/manifest-admin.json'
];

// Instalar Service Worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// Activar Service Worker
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// ==========================================
// MANEJO DE NOTIFICACIONES PUSH
// ==========================================
self.addEventListener('push', event => {
  console.log('🔔 Notificación push recibida:', event);
  
  let datos = { titulo: 'Luna Delivery', mensaje: 'Nuevo evento' };
  
  try {
    if (event.data) {
      datos = event.data.json();
    }
  } catch (e) {
    console.error('Error al parsear datos push:', e);
  }
  
  const opciones = {
    body: datos.mensaje || 'Tienes una nueva notificación',
    icon: '/static/icon-192x192.png', // Tu logo
    badge: '/static/badge-72x72.png', // Badge pequeño
    vibrate: [200, 100, 200],
    tag: 'luna-delivery-notification',
    requireInteraction: true,
    data: {
      url: datos.url || '/admin'
    }
  };
  
  event.waitUntil(
    self.registration.showNotification(datos.titulo || 'Luna Delivery', opciones)
  );
});

// ==========================================
// CUANDO SE HACE CLIC EN LA NOTIFICACIÓN
// ==========================================
self.addEventListener('notificationclick', event => {
  console.log('️ Click en notificación:', event);
  
  event.notification.close();
  
  const urlParaAbrir = event.notification.data?.url || '/admin';
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(windowClients => {
        // Verificar si ya hay una ventana abierta
        for (let client of windowClients) {
          if (client.url === urlParaAbrir && 'focus' in client) {
            return client.focus();
          }
        }
        // Si no, abrir una nueva ventana
        if (clients.openWindow) {
          return clients.openWindow(urlParaAbrir);
        }
      })
  );
});

// ==========================================
// MANEJO DE FETCH (opcional, para offline)
// ==========================================
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});