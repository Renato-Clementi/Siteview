/* GIRO ESCo · BABOO · service worker
   Strategia: navigazioni network-first (gli aggiornamenti da GitHub arrivano subito),
   con fallback alla copia in cache quando manca la rete. Icone e manifest cache-first.
   Le chiamate esterne (Anthropic, OpenAI, Nominatim, Whisper) NON vengono intercettate. */
const CACHE = 'giro-esco-v1';
const SHELL = ['./', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'icon-512-maskable.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return; /* API esterne: passano dirette */

  if (req.mode === 'navigate') {
    /* pagina: prima la rete (versione fresca), poi la fotocopia */
    e.respondWith(
      fetch(req).then(r => {
        const copy = r.clone();
        caches.open(CACHE).then(c => c.put('./', copy));
        return r;
      }).catch(() => caches.match('./', { ignoreSearch: true }))
    );
    return;
  }

  /* risorse dell'app (icone, manifest): prima la cache, poi la rete */
  e.respondWith(
    caches.match(req, { ignoreSearch: true }).then(hit => hit || fetch(req).then(r => {
      if (r.ok) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
      return r;
    }))
  );
});
