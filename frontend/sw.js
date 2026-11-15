// Caches the app shell so the app opens offline (section 9). API calls always go to the network.
const SHELL = "field-shift-shell-v12";
const FILES = ["/", "/workspace/", "/science/", "/styles.css?v=7", "/site.css?v=7", "/workspace.css?v=7", "/theme.css?v=9", "/science.css", "/app.js?v=12", "/soil-profile.js?v=2", "/home.js?v=6", "/science.js", "/map-layers.js?v=6", "/assets/field-study.svg", "/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((cache) => cache.addAll(FILES)).then(()=>self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith('field-shift-shell-') && k !== SHELL).map((k) => caches.delete(k)))).then(()=>self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin!==self.location.origin || !FILES.some((file)=>new URL(file,self.location.origin).pathname===url.pathname)) return;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if(response.ok){const copy = response.clone();caches.open(SHELL).then((cache) => cache.put(event.request, copy));}
        return response;
      })
      .catch(() => caches.match(event.request).then((hit) => hit || caches.match(url.pathname)).then((hit) => hit || Response.error()))
  );
});
