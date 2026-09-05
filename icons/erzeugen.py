#!/usr/bin/env python3
"""Erzeugt die App-Icons in den Farben der Hauptseite.

    python icons/erzeugen.py

Sonne in Bernstein, Wolke in Gedaempft, Grund wie clara_working_station.
Zwei Sorten, weil Android sie unterschiedlich behandelt:

  icon-<n>.png        "any"      - das Motiv fuellt die Flaeche
  icon-maskable-<n>.png "maskable" - Android schneidet daraus einen Kreis,
                        ein Herz oder was der Hersteller mag. Alles Wichtige
                        muss im inneren Kreis von 80 % liegen, sonst wird es
                        abgeschnitten.
"""

from pathlib import Path

from PIL import Image, ImageDraw

GRUND = (8, 17, 12)         # --bg    #08110c  (moos)
SONNE = (242, 181, 68)      # --accent #f2b544
WOLKE = (135, 164, 147)     # --muted  #87a493
HELL = (232, 242, 234)      # --ink    #e8f2ea

HIER = Path(__file__).resolve().parent


def zeichnen(px, maskable):
    # Bei maskable muss das Motiv kleiner sein - der Rand wird weggeschnitten.
    gross = px * 4                       # vierfach zeichnen, dann verkleinern
    bild = Image.new("RGBA", (gross, gross), GRUND + (255,))
    d = ImageDraw.Draw(bild)

    m = gross / 2
    skala = 0.62 if maskable else 0.80   # Sicherheitszone fuer maskable
    e = gross * skala / 2                # halbe Motivbreite

    # Sonne oben links, teils hinter der Wolke
    sr = e * 0.46
    sx, sy = m - e * 0.34, m - e * 0.40
    d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=SONNE)

    # Strahlen - nur bei der grossen Fassung, sonst matschen sie zu
    if px >= 180:
        import math
        for i in range(8):
            w = math.radians(i * 45 + 22.5)
            x0, y0 = sx + math.cos(w) * sr * 1.28, sy + math.sin(w) * sr * 1.28
            x1, y1 = sx + math.cos(w) * sr * 1.62, sy + math.sin(w) * sr * 1.62
            d.line([x0, y0, x1, y1], fill=SONNE, width=int(gross * 0.022))

    # Wolke: drei Ballen und ein Sockel
    wy = m + e * 0.30
    wx = m + e * 0.06
    r1, r2, r3 = e * 0.40, e * 0.52, e * 0.34
    d.ellipse([wx - e * 0.74 - r1, wy - r1, wx - e * 0.74 + r1, wy + r1], fill=WOLKE)
    d.ellipse([wx - e * 0.10 - r2, wy - r2 * 1.15, wx - e * 0.10 + r2, wy + r2 * 0.85], fill=WOLKE)
    d.ellipse([wx + e * 0.56 - r3, wy - r3, wx + e * 0.56 + r3, wy + r3], fill=WOLKE)
    d.rounded_rectangle([wx - e * 0.86, wy - e * 0.02, wx + e * 0.86, wy + e * 0.40],
                        radius=e * 0.20, fill=WOLKE)

    return bild.resize((px, px), Image.LANCZOS)


def main():
    HIER.mkdir(parents=True, exist_ok=True)
    gemacht = []
    for px in (192, 512):
        zeichnen(px, False).save(HIER / ("icon-%d.png" % px))
        gemacht.append("icon-%d.png" % px)
        zeichnen(px, True).save(HIER / ("icon-maskable-%d.png" % px))
        gemacht.append("icon-maskable-%d.png" % px)
    # iOS nimmt kein maskable und kein Manifest-Icon - es will apple-touch-icon
    zeichnen(180, False).save(HIER / "apple-touch-icon.png")
    gemacht.append("apple-touch-icon.png")
    # Favicon fuer den Tab
    zeichnen(32, False).save(HIER / "favicon-32.png")
    gemacht.append("favicon-32.png")

    for n in gemacht:
        p = HIER / n
        print("  %-26s %6d Byte" % (n, p.stat().st_size))


if __name__ == "__main__":
    main()
