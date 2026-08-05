'use strict';

const VERSION = 'tfp-v4';
const SHELL = `${VERSION}-shell`;
const FRAMES = `${VERSION}-frames`;
const SHELL_FILES = ['./', './index.html', './logo.svg', './og-image.svg', './manifest.webmanifest'];

let lastFrameRequestAt = 0;
let idleCacheTimer = null;
let idleCacheRunning = false;
const pendingFrameUrls = new Set();

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
      .then(keys => Promise.all(
        keys
          .filter(key => key.startsWith('tfp-') && ![SHELL, FRAMES].includes(key))
          .map(key => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

function scheduleIdleCache() {
  clearTimeout(idleCacheTimer);
  idleCacheTimer = setTimeout(() => {
    cachePendingFrames().catch(() => {});
  }, 1800);
}

async function cachePendingFrames() {
  if (idleCacheRunning || !pendingFrameUrls.size) return;
  if (Date.now() - lastFrameRequestAt < 1700) {
    scheduleIdleCache();
    return;
  }

  idleCacheRunning = true;
  const cache = await caches.open(FRAMES);

  try {
    while (pendingFrameUrls.size) {
      if (Date.now() - lastFrameRequestAt < 900) break;

      const url = pendingFrameUrls.values().next().value;
      pendingFrameUrls.delete(url);
      const request = new Request(url, { credentials: 'same-origin' });

      try {
        const exists = await cache.match(request);
        if (!exists) {
          const response = await fetch(request);
          if (response.ok) await cache.put(request, response);
        }
      } catch (_) {}

      // One slow cache operation at a time, only while the user is idle.
      await sleep(180);
    }
  } finally {
    idleCacheRunning = false;
    if (pendingFrameUrls.size) scheduleIdleCache();
  }
}

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  const isFrame = url.pathname.includes('/frame/movil/webp/');
  if (isFrame) {
    lastFrameRequestAt = Date.now();
    pendingFrameUrls.add(request.url);
    scheduleIdleCache();

    event.respondWith((async () => {
      const cache = await caches.open(FRAMES);
      const cached = await cache.match(request);
      if (cached) return cached;

      // Return the network response immediately. Do not write to Cache Storage
      // during active scrolling because that was competing with canvas decoding.
      return fetch(request);
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

self.addEventListener('message', event => {
  const data = event.data || {};
  if (data.type !== 'CACHE_FRAMES' || !Array.isArray(data.urls)) return;

  for (const value of data.urls) {
    try {
      const url = new URL(value, self.location.href);
      if (url.origin === self.location.origin) pendingFrameUrls.add(url.href);
    } catch (_) {}
  }
  scheduleIdleCache();
});