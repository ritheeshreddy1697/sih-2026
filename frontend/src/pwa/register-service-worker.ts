export function registerServiceWorker() {
  if (!import.meta.env.PROD || !("serviceWorker" in navigator)) return;

  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js", { scope: "/" }).then((registration) => {
      if (registration.waiting) window.dispatchEvent(new Event("ncct:pwa-update-ready"));
      registration.addEventListener("updatefound", () => {
        const worker = registration.installing;
        worker?.addEventListener("statechange", () => {
          if (worker.state === "installed" && navigator.serviceWorker.controller) {
            window.dispatchEvent(new Event("ncct:pwa-update-ready"));
          }
        });
      });
    }).catch(() => undefined);
  });
}

export function cacheCurrentPageAssets() {
  const controller = navigator.serviceWorker?.controller;
  if (!controller) return;
  const urls = performance
    .getEntriesByType("resource")
    .map((entry) => entry.name)
    .filter((url) => {
      const parsed = new URL(url);
      return parsed.origin === window.location.origin && parsed.pathname.startsWith("/assets/");
    });
  controller.postMessage({ type: "CACHE_URLS", urls: [...new Set(urls)] });
}
