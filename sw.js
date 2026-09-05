/* Service Worker fuer "Wetter Berlin".
 *
 * Zwei Strategien, weil hier zwei verschiedene Sorten Daten liegen:
 *
 *   Huelle (HTML, Manifest, Icons)  -> cache first, im Hintergrund erneuern.
 *      Aendert sich selten. So startet die App auch ohne Netz sofort.
 *
 *   Daten (Open-Meteo, Zusammenfassung) -> network first, Cache als Rueckfall.
 *      Aendert sich stuendlich. Veraltete Werte sind besser als eine leere
 *      Seite, aber nur wenn nichts Neues zu holen ist. Die Seite markiert
 *      sie dann sichtbar als alt.
 *
 * VERSION bei jeder Aenderung der Huelle hochzaehlen, sonst behalten
 * installierte Geraete die alte Fassung, bis der Cache verfaellt.
 */
const VERSION = "v5";
const HUELLE = "wetter-huelle-" + VERSION;
const DATEN  = "wetter-daten-" + VERSION;

const VORRAT = [
  "./",
  "./wetter.html",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/apple-touch-icon.png",
  "./icons/favicon-32.png",
];

self.addEventListener("install", e => {
  // addAll bricht komplett ab, wenn eine Datei fehlt - deshalb einzeln,
  // damit ein fehlendes Icon nicht die ganze Installation verhindert.
  e.waitUntil((async () => {
    const c = await caches.open(HUELLE);
    await Promise.all(VORRAT.map(u => c.add(new Request(u, {cache: "reload"}))
                                       .catch(() => {})));
    self.skipWaiting();
  })());
});

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    const behalten = [HUELLE, DATEN];
    for (const name of await caches.keys())
      if (!behalten.includes(name)) await caches.delete(name);
    await self.clients.claim();
  })());
});

const istDaten = url =>
  url.hostname.endsWith("open-meteo.com") ||
  url.pathname.endsWith("zusammenfassung.json");

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;

  let url;
  try { url = new URL(req.url); } catch (_) { return; }
  if (url.protocol !== "https:" && url.protocol !== "http:") return;

  // --- Daten: erst Netz, dann Cache ------------------------------------
  if (istDaten(url)) {
    // Schluessel ohne Query. Zwei Gruende: die Seite haengte einen
    // Zeitstempel an (?t=...), womit jeder Aufruf einen eigenen Eintrag
    // erzeugt haette und der Rueckfall NIE getroffen haette. Und ein
    // Request mit cache:"no-store" laesst sich gar nicht ablegen - ein
    // frischer Request ohne diese Einstellung schon.
    const schluessel = new Request(url.origin + url.pathname);
    e.respondWith((async () => {
      try {
        const antwort = await fetch(req);
        if (antwort && antwort.ok) {
          const c = await caches.open(DATEN);
          await c.put(schluessel, antwort.clone()).catch(() => {});
        }
        return antwort;
      } catch (_) {
        const alt = await caches.match(schluessel);
        if (alt) return alt;
        // Ohne Netz UND ohne Cache: die Seite faengt das ab und zeigt
        // ihren localStorage-Stand.
        return new Response(JSON.stringify({error: "offline"}), {
          status: 503, headers: {"Content-Type": "application/json"}});
      }
    })());
    return;
  }

  // --- Huelle: erst Cache, dann im Hintergrund erneuern -----------------
  if (url.origin === self.location.origin) {
    e.respondWith((async () => {
      const treffer = await caches.match(req);
      const frisch = fetch(req).then(async antwort => {
        if (antwort && antwort.ok) {
          const c = await caches.open(HUELLE);
          c.put(req, antwort.clone());
        }
        return antwort;
      }).catch(() => null);

      if (treffer) return treffer;
      const antwort = await frisch;
      if (antwort) return antwort;
      // Navigation ohne Netz und ohne Treffer: die Startseite anbieten
      if (req.mode === "navigate") {
        const start = await caches.match("./wetter.html");
        if (start) return start;
      }
      return new Response("offline", {status: 503});
    })());
  }
});
