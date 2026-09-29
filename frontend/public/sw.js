const CACHE_VERSION = "ncct-shell-v1";
const SHELL_URLS = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
  "/icons/ncct-192.png",
  "/icons/ncct-512.png",
];

async function cacheApplicationShell() {
  const cache = await caches.open(CACHE_VERSION);
  await Promise.all(
    SHELL_URLS.map(async (url) => {
      try {
        const response = await fetch(url, { cache: "reload" });
        if (response.ok) await cache.put(url, response);
      } catch {
        // A previous shell remains usable when an update check happens offline.
      }
    }),
  );

  const indexResponse = await cache.match("/index.html");
  if (!indexResponse) return;
  const html = await indexResponse.text();
  const assetUrls = [...html.matchAll(/(?:src|href)="(\/assets\/[^"]+)"/g)].map(
    (match) => match[1],
  );
  await Promise.all(
    assetUrls.map(async (url) => {
      try {
        const response = await fetch(url, { cache: "reload" });
        if (response.ok) await cache.put(url, response);
      } catch {
        // The HTML shell still provides a useful offline recovery screen.
      }
    }),
  );
}

self.addEventListener("install", (event) => {
  event.waitUntil(cacheApplicationShell());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    Promise.all(
      [
        caches.keys().then((keys) =>
          Promise.all(keys.filter((key) => key !== CACHE_VERSION).map((key) => caches.delete(key))),
        ),
        self.clients.claim(),
      ],
    ),
  );
});

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") self.skipWaiting();
  if (event.data?.type === "CACHE_URLS" && Array.isArray(event.data.urls)) {
    const urls = event.data.urls.filter((value) => {
      const url = new URL(value, self.location.origin);
      return url.origin === self.location.origin && url.pathname.startsWith("/assets/");
    });
    event.waitUntil(
      caches.open(CACHE_VERSION).then((cache) => Promise.all(urls.map((url) => cache.add(url)))),
    );
  }
});

function isPrivateRequest(request, url) {
  return (
    url.pathname.startsWith("/api/") ||
    request.headers.has("Authorization") ||
    request.method !== "GET"
  );
}

async function navigationResponse(request) {
  const cache = await caches.open(CACHE_VERSION);
  try {
    const response = await fetch(request);
    if (response.ok) await cache.put("/index.html", response.clone());
    return response;
  } catch {
    return (
      (await cache.match("/index.html")) ??
      new Response(
        "<!doctype html><html lang=\"en\"><meta name=\"viewport\" content=\"width=device-width\"><title>NCCT Training</title><body><main><h1>NCCT Training</h1><p>The app shell is not available yet. Connect once and reopen the app.</p></main></body></html>",
        { headers: { "Content-Type": "text/html; charset=utf-8" } },
      )
    );
  }
}

async function staticAssetResponse(request) {
  const cache = await caches.open(CACHE_VERSION);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok && response.type === "basic") await cache.put(request, response.clone());
  return response;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (isPrivateRequest(request, url)) return;
  if (url.origin !== self.location.origin) return;
  if (request.mode === "navigate") {
    event.respondWith(navigationResponse(request));
    return;
  }
  if (["script", "style", "font", "image"].includes(request.destination)) {
    event.respondWith(staticAssetResponse(request));
  }
});
