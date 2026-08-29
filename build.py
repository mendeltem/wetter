#!/usr/bin/env python3
"""Holt die Berliner Vorhersage, laesst das lokale Modell sie in Worte fassen,
schreibt zusammenfassung.json und schiebt sie ins Repo.

Die Zahlen auf der Seite holt der Browser selbst - die sind also auch dann
aktuell, wenn dieser Lauf ausfaellt. Hier entsteht nur der Fliesstext.

Rueckgabewerte:
  0  Zusammenfassung erneuert (oder unveraendert, nichts zu tun)
  1  Wetterdaten nicht erreichbar
  2  lokales Modell nicht erreichbar - Seite bleibt mit alter Zusammenfassung
"""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent
OUT = REPO / "zusammenfassung.json"
LOG = REPO / "build.log"

LLM = "http://127.0.0.1:8080/v1/chat/completions"
STARTER = Path(r"C:\Users\Mendel\Projects\lok\start-llm.ps1")

METEO = ("https://api.open-meteo.com/v1/forecast"
         "?latitude=52.52&longitude=13.405"
         "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m"
         "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
         "precipitation_sum,precipitation_probability_max,wind_speed_10m_max"
         "&timezone=Europe%2FBerlin&forecast_days=7")

WMO = {0: "klar", 1: "ueberwiegend klar", 2: "teils bewoelkt", 3: "bedeckt",
       45: "Nebel", 48: "Reifnebel", 51: "leichter Niesel", 53: "Niesel",
       55: "starker Niesel", 61: "leichter Regen", 63: "Regen", 65: "starker Regen",
       71: "leichter Schnee", 73: "Schnee", 75: "starker Schnee",
       80: "Regenschauer", 81: "Regenschauer", 82: "heftige Schauer",
       85: "Schneeschauer", 86: "starke Schneeschauer",
       95: "Gewitter", 96: "Gewitter mit Hagel", 99: "schweres Gewitter"}
DOW = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def log(msg):
    line = "%s  %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line)
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def wetter():
    with urllib.request.urlopen(METEO, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def als_text(d):
    """Die Vorhersage als knappe Tabelle - das ist die Eingabe fuer das Modell."""
    c, dd = d["current"], d["daily"]
    zeilen = ["Jetzt: %.0f Grad, gefuehlt %.0f, %s, Wind %.0f km/h." % (
        c["temperature_2m"], c["apparent_temperature"],
        WMO.get(c["weather_code"], "?"), c["wind_speed_10m"])]
    for i, iso in enumerate(dd["time"]):
        tag = datetime.strptime(iso, "%Y-%m-%d")
        zeilen.append("%s %s: %.0f bis %.0f Grad, %s, Regenrisiko %d Prozent, "
                      "%.1f mm, Wind bis %.0f km/h." % (
                          "Heute" if i == 0 else DOW[tag.weekday()],
                          tag.strftime("%d.%m."),
                          dd["temperature_2m_min"][i], dd["temperature_2m_max"][i],
                          WMO.get(dd["weather_code"][i], "?"),
                          dd["precipitation_probability_max"][i],
                          dd["precipitation_sum"][i], dd["wind_speed_10m_max"][i]))
    return "\n".join(zeilen)


def server_da(timeout=5):
    try:
        urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=timeout)
        return True
    except Exception:
        return False


def server_starten(wartezeit=600):
    """Startet llama-server im Hintergrund und wartet, bis er antwortet."""
    if not STARTER.is_file():
        return False
    log("llama-server laeuft nicht, starte %s" % STARTER.name)
    subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                      "-WindowStyle", "Hidden", "-File", str(STARTER)],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ende = time.time() + wartezeit
    while time.time() < ende:
        if server_da(3):
            log("Server bereit")
            return True
        time.sleep(10)
    log("Server kam innerhalb von %d s nicht hoch" % wartezeit)
    return False


def zusammenfassen(vorhersage):
    system = ("Antworte nur mit dem Ergebnis. Keine Einleitung, keine Aufzaehlung, "
              "keine Schlussfloskel.\n"
              "Arbeite ausschliesslich mit den gelieferten Zahlen. Erfinde nichts, "
              "nenne keine Werte, die nicht dastehen.\n"
              "Schreibe drei bis vier Saetze Fliesstext auf Deutsch fuer jemanden, der "
              "morgens wissen will, was ihn erwartet: erst heute, dann die Tendenz der "
              "Woche, und ob eine Jacke oder ein Schirm noetig ist.")
    body = {"model": "local",
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": vorhersage}],
            "temperature": 0.3, "max_tokens": 300,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(LLM, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.loads(r.read().decode("utf-8"))
    txt = (d["choices"][0]["message"].get("content") or "").strip()
    import re
    txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.S).strip()
    t = d.get("timings") or {}
    log("Modell antwortete in %.1f s (decode %.1f t/s)"
        % (time.time() - t0, t.get("predicted_per_second") or 0))
    return txt, d.get("model") or "lokales Modell"


def pushen():
    def git(*a):
        return subprocess.run(["git", "-C", str(REPO)] + list(a),
                              capture_output=True, text=True)
    if not git("status", "--porcelain").stdout.strip():
        log("nichts geaendert, kein Commit")
        return
    git("add", "zusammenfassung.json")
    stamp = datetime.now().strftime("%Y-%m-%d")
    r = git("commit", "-m", "Zusammenfassung %s" % stamp)
    if r.returncode:
        log("commit fehlgeschlagen: %s" % (r.stderr or r.stdout).strip()[:200])
        return
    r = git("push")
    if r.returncode:                      # erster Lauf: noch kein Upstream
        r = git("push", "-u", "origin", "HEAD")
    log("push: %s" % ("ok" if r.returncode == 0
                      else (r.stderr or r.stdout).strip()[:200]))


def main():
    log("--- Lauf gestartet ---")
    try:
        d = wetter()
    except Exception as e:
        log("Wetterdaten nicht erreichbar: %s" % e)
        return 1

    vorhersage = als_text(d)
    log("Vorhersage geholt: %d Tage" % len(d["daily"]["time"]))

    if not server_da() and not server_starten():
        log("ohne lokales Modell - alte Zusammenfassung bleibt stehen")
        return 2

    try:
        text, modell = zusammenfassen(vorhersage)
    except Exception as e:
        log("Modell antwortete nicht: %s" % e)
        return 2

    if not text:
        log("leere Antwort, nichts geschrieben")
        return 2

    OUT.write_text(json.dumps({
        "text": text,
        "erstellt": datetime.now().strftime("%d.%m.%Y um %H:%M"),
        "modell": Path(str(modell)).name or "lokales Modell",
        "grundlage": vorhersage,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    log("geschrieben: %s (%d Zeichen)" % (OUT.name, len(text)))
    pushen()
    log("--- fertig ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
