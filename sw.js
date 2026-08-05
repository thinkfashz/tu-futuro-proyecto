'use strict';
const VERSION='tfp-v2';
const SHELL=`${VERSION}-shell`;
const FRAMES=`${VERSION}-frames`;
const SHELL_FILES=['./','./index.html','./logo.svg','./og-image.svg','./manifest.webmanifest'];
self.addEventListener('install',event=>event.waitUntil(caches.open(SHELL).then(cache=>Promise.allSettled(SHELL_FILES.map(url=>cache.add(url)))).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>!key.startsWith(VERSION)).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
  const request=event.request;if(request.method!=='GET')return;
  const url=new URL(request.url);
  if(url.origin!==location.origin)return;
  const isFrame=url.pathname.includes('/frame/movil/webp/');
  if(isFrame){event.respondWith(caches.open(FRAMES).then(async cache=>{const hit=await cache.match(request);if(hit)return hit;const response=await fetch(request);if(response.ok)cache.put(request,response.clone()).catch(()=>{});return response}));return}
  event.respondWith(caches.open(SHELL).then(async cache=>{try{const fresh=await fetch(request);if(fresh.ok)cache.put(request,fresh.clone()).catch(()=>{});return fresh}catch{const cached=await cache.match(request);return cached||Response.error()}}));
});