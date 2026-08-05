'use strict';

const VERSION = 'tfp-v3';
const SHELL = `${VERSION}-shell`;
const FRAMES = `${VERSION}-frames`;
const SHELL_FILES = ['./', './index.html', './logo.svg', './og-image.svg', './manifest.webmanifest'];

let cachePaused = false;
let cacheQueue = [];
let cacheRunning = false;

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(SHELL)
      .then(cache => Promise.allSettled(SHELL_FILES.map(url => cache.add(url))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key.startsWith('tfp-') && ![SHELL, FRAMES].includes(key)).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  const isFrame = url.pathname.includes('/frame/movil/webp/');
  if (isFrame) {
    event.respondWith((async () => {
      const cache = await caches.open(FRAMES);
      const cached = await cache.match(request);
      if (cached) return cached;

      const response = await fetch(request);
      if (response.ok) {
        event.waitUntil(cache.put(request, response.clone()).catch(() => {}));
      }
      return response;
    })());
    return;
  }

  event.respondWith((async () => {
    const cache = await caches.open(SHELL);
    try {
      const fresh = await fetch(request);
      if (fresh.ok) event.waitUntil(cache.put(request, fresh.clone()).catch(() => {}));
      return fresh;
    } catch (_) {
      return (await cache.match(request)) || Response.error();
    }
  })());
});

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function runCacheQueue() {
  if (cacheRunning) return;
  cacheRunning = true;
  const cache = await caches.open(FRAMES);

  try {
    while (cacheQueue.length) {
      if (cachePaused) {
        await sleep(250);
        continue;
      }

      const url = cacheQueue.shift();
      const request = new Request(url, { credentials: 'same-origin' });
      try {
        const exists = await cache.match(request);
        if (!exists) {
          const response = await fetch(request);
          if (response.ok) await cache.put(request, response);
        }
      } catch (_) {}

      // Give scrolling, GSAP and canvas painting priority over background cache writes.
      await sleep(140);
    }
  } finally {
    cacheRunning = false;
  }
}

self.addEventListener('message', event => {
  const data = event.data || {};

  if (data.type === 'PAUSE_FRAME_CACHE') {
    cachePaused = true;
    return;
  }

  if (data.type === 'RESUME_FRAME_CACHE') {
    cachePaused = false;
    event.waitUntil(runCacheQueue());
    return;
  }

  if (data.type === 'CACHE_FRAMES' && Array.isArray(data.urls)) {
    const known = new Set(cacheQueue);
    for (const url of data.urls) {
      try {
        const parsed = new URL(url, self.location.href);
        if (parsed.origin === self.location.origin && !known.has(parsed.href)) {
          known.add(parsed.href);
          cacheQueue.push(parsed.href);
        }
      } catch (_) {}
    }
    event.waitUntil(runCacheQueue());
  }
});