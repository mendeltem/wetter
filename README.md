# wetter

Wetterseite für Berlin. **[Zur Seite →](https://mendeltem.github.io/wetter/wetter.html)**

## Wie sie funktioniert

Zwei getrennte Wege, absichtlich:

**Die Zahlen** holt der Browser bei jedem Aufruf selbst von
[Open-Meteo](https://open-meteo.com/) — ohne API-Schlüssel, ohne Server dazwischen.
Die Seite ist damit immer aktuell, auch wenn wochenlang niemand etwas baut. Alle
zehn Minuten lädt sie im Hintergrund nach.

**Den Fließtext** schreibt jeden Morgen um 6 Uhr ein Sprachmodell auf dem eigenen
Rechner — kein Cloud-Dienst, keine Kosten. `build.py` holt die Vorhersage, legt sie
dem Modell vor, schreibt `zusammenfassung.json` und schiebt sie hierher.

Fällt der Lauf aus, weil der Rechner aus war, bleibt die letzte Zusammenfassung
stehen und die Zahlen stimmen trotzdem. Das ist der Grund für die Trennung.

## Dateien

| | |
|---|---|
| `wetter.html` | die Seite — eigenständig, kein Build-Schritt, keine Abhängigkeiten |
| `build.py` | der 6-Uhr-Lauf: Vorhersage holen, Modell fragen, committen |
| `zusammenfassung.json` | was das Modell heute geschrieben hat, samt Zahlengrundlage |

## Selbst laufen lassen

```bash
python build.py
```

Läuft der lokale Server nicht, startet `build.py` ihn und wartet bis zu zehn
Minuten. Antwortet er nicht, endet der Lauf mit Code 2 und lässt die alte
Zusammenfassung stehen — die Seite bleibt benutzbar.

Der lokale Teil stammt aus [local_models](https://github.com/mendeltem/local_models).
