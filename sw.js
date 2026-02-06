const CACHE_NAME = 'juicepick-v12'; // v12: Default Sort Price Low

// Minimal install - just register, no pre-caching to avoid failures
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  console.log('[SW v12] Installing...');
  self.skipWaiting(); // Force immediate activation
});

// Listen for SKIP_WAITING message from client
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('activate', (event) => {
  console.log('[SW v8] Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          // Delete ALL old caches
          if (cacheName !== CACHE_NAME) {
            console.log('[SW v8] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW v8] Taking control of all clients');
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Skip non-HTTP requests
  if (!url.protocol.startsWith('http')) return;

  // Skip external resources (CDNs, Firebase, etc.) - let browser handle them
  if (!url.origin.includes('juicepick.github.io') && !url.origin.includes('localhost')) {
    return;
  }

  // NETWORK-FIRST for EVERYTHING to ensure freshness
  event.respondWith(
    fetch(event.request, { cache: 'no-cache' })
      .then((response) => {
        // Clone and cache successful responses
        if (response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // Only use cache when offline
        console.log('[SW v8] Network failed, trying cache for:', event.request.url);
        return caches.match(event.request);
      })
  );
});
