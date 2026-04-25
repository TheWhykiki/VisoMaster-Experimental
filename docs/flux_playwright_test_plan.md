# FLUX GUI Playwright Test Plan

## Ziel

Der Browser-Client soll autark testen koennen, ob ein einfacher ACE++ / FLUX Swap ueber die Web-GUI bedienbar ist. Der Test prueft nicht nur einzelne API-Endpunkte, sondern den echten Browserfluss:

1. WebUI laden und JavaScript-/Console-Fehler sammeln.
2. Workbench auf `ACE++ (FLUX)` stellen.
3. FLUX-Controls sichtbar machen und sichere Defaults setzen.
4. Target-Medium und Source-Face ueber die GUI hochladen.
5. Detection-Frame erzeugen.
6. `Find Faces` ausloesen und erkannte Zielgesichter validieren.
7. `Swap Preview` ausloesen und die geswappte Vorschau validieren.
8. `Swap Faces` starten und erfolgreichen Output-Status validieren.

## Zwei Betriebsarten

`stub` ist der schnelle Pflichttest fuer Entwicklung und CI. Er startet einen isolierten lokalen Webserver, simuliert Face Detection, FLUX Preview und Output-Datei serverseitig und beweist damit die GUI-Verkabelung ohne GPU, Diffusers-Download oder echte Modelle.

`real` ist der Host-Test fuer Windows/Linux mit GPU. Er benutzt echte Target-/Source-Dateien und laesst die existierende Headless-Pipeline inklusive ACE++ / FLUX laufen. Dafuer muessen Runtime, Modelle, Hugging-Face-Zugriff und Playwright-Browser auf dem Host vorhanden sein.

## Befehle

Schneller GUI-/FLUX-Smoke-Test:

```bash
python scripts/playwright_flux_swap_audit.py --mode stub
```

Optional im Quality-Gate:

```bash
python scripts/gui_quality_gate.py --with-playwright
```

Echter FLUX-Test auf dem GPU-Host:

```bash
python scripts/playwright_flux_swap_audit.py \
  --mode real \
  --target /path/to/target_face.png \
  --source /path/to/source_face.png \
  --timeout-ms 600000
```

Gegen einen bereits laufenden Webserver:

```bash
python scripts/playwright_flux_swap_audit.py \
  --mode real \
  --url http://127.0.0.1:8000 \
  --target /path/to/target_face.png \
  --source /path/to/source_face.png
```

## Playwright Setup

Falls Playwright noch nicht eingerichtet ist:

```bash
python -m pip install playwright
python -m playwright install chromium
```

Im Projekt-Environment ist das Python-Paket ueber `requirements_cu129.txt` vorgesehen. Die Browser-Installation bleibt bewusst ein expliziter Schritt, weil sie plattformspezifische Binaries herunterlaedt.

## Validierungskriterien

Der Test gilt als erfolgreich, wenn:

- die WebUI ohne Page-Error startet,
- die FLUX-Controls im Browser sichtbar und bedienbar sind,
- Target und Source in den GUI-Panels erscheinen,
- ein Preview Frame registriert wird,
- `Find Faces` mindestens ein Target-Face registriert,
- `Swap Preview` ein Bild in der rechten Preview anzeigt,
- `Swap Faces` mit `succeeded` endet und ein Output-Pfad existiert.

Im `real`-Modus ist ein Fehlschlag absichtlich hart: so sehen wir sofort, ob Runtime, Modelle, Face Detection oder FLUX-Inferenz auf dem GPU-Host noch nicht stimmen.
