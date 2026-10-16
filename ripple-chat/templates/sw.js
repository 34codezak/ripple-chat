{% load static %}/* Ripple-Chat service worker — rendered by Django, served at /sw.js */
const VERSION = "{{ cache_version }}";
const STATIC_CACHE = `ripple-static-${VERSION}`;
const PAGE_CACHE = `ripple-pages-${VERSION}`;
const OFFLINE_URL = "/offline/";

const PRECACHE = [
  OFFLINE_URL,
  "{% static 'css/app.css' %}",
  "{% static 'manifest.json' %}",
  "{% static 'icons/icon-192.png' %}",
  "{% static 'icons/icon-512.png' %}",
  "{% static 'illustrations/slide-1.svg' %}",
  "{% static 'illustrations/slide-2.svg' %}",
  "{% static 'illustrations/slide-3.svg' %}",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    Promise.all([
      caches.open(STATIC_CACHE).then((c) => c.addAll(PRECACHE.filter((u) => u !== OFFLINE_URL))),
      caches.open(PAGE_CACHE).then((c) => c.add(OFFLINE_URL)),
    ]).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => ![STATIC_CACHE, PAGE_CACHE].includes(k)).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// Cache First: static assets (CSS/JS/icons)
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) {
    const cache = await caches.open(STATIC_CACHE);
    cache.put(request, response.clone());
  }
  return response;
}

// Network First: HTML navigations, falling back to cache, then the offline page
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(PAGE_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    return (await caches.match(request)) || (await caches.match(OFFLINE_URL));
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return; // never touch POSTs (HTMX sends)

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return; // CDN scripts etc. go to the network

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(cacheFirst(request));
  } else if (request.mode === "navigate") {
    event.respondWith(networkFirst(request));
  }
  // Everything else (HTMX fragments, admin XHR, WebSockets) is left alone.
});
