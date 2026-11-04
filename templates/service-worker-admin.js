// Service Worker para notificaciones push (Modo Admin)
const CACHE_NAME = 'luna-admin-v2';

// Instalar
self.addEventListener('install', event => {
  self.skipWaiting();
});

// Activar
self.addEventListener('activate', event => {
  self.clients.claim();
});

// ==========================================
// MANEJO DE NOTIFICACIONES PUSH
// ==========================================
self.addEventListener('push', event => {
  console.log('🔔 Push recibido:', event);
  
  let datos = { 
    titulo: 'Luna Delivery', 
    mensaje: 'Nuevo evento',
    url: '/admin'
  };
  
  try {
    if (event.data) {
      datos = event.data.json();
    }
  } catch (e) {
    console.error('Error parseando push:', e);
  }
  
  const opciones = {
    body: datos.mensaje,
    icon: 'https://drive.google.com/thumbnail?id=1jOiiRWxhyXF_wA7ObkKYVjd9PTlmXPvd&sz=w192',
    badge: 'https://drive.google.com/thumbnail?id=1jOiiRWxhyXF_wA7ObkKYVjd9PTlmXPvd&sz=w72',
    vibrate: [200, 100, 200],
    tag: 'luna-notification',
    requireInteraction: true,
    data: {
      url: datos.url || '/admin'
    }
  };
  
  event.waitUntil(
    self.registration.showNotification(datos.titulo, opciones)
  );
});

// Click en notificación
self.addEventListener('notificationclick', event => {
  console.log('Click notificación');
  event.notification.close();
  
  const url = event.notification.data?.url || '/admin';
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clients => {
        for (let client of clients) {
          if (client.url.includes('admin') && 'focus' in client) {
            return client.focus();
          }
        }
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
  );
});