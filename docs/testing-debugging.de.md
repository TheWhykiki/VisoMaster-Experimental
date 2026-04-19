# Testing- und Debugging-Konzept fuer die Web-GUI

## Ziel

Die Web-GUI darf nicht mehr nur per Sichtpruefung bewertet werden. Wir brauchen einen Ablauf, den ich hier selbststaendig starten, auswerten und bei Fehlern mit verwertbaren Artefakten weiterverfolgen kann.

## Prinzip

Die Absicherung ist in drei Schichten aufgeteilt:

1. `Syntax + Dateivertrag`
   Python- und JavaScript-Syntax muessen zuerst sauber sein.
   HTML und JS muessen denselben DOM-Vertrag einhalten, damit fehlende IDs sofort auffallen.

2. `Isolierte Web-Smokes`
   Die Tests fuer Workbench, Browser-Workflow und HTTP-Endpunkte laufen mit temporaeren Pfaden.
   Dadurch wird der echte `.web`-Zustand nicht geloescht oder verfremdet.

3. `Debug-Bundle`
   Wenn etwas schiefgeht, wird ein reproduzierbares Bundle mit API-Snapshots, Static-Dateien, Git-Status und Laufzeitdateien erzeugt.
   Damit kann ich Fehler ohne Rueckfrage weiter untersuchen.

## Neue Werkzeuge

### `python3 scripts/gui_quality_gate.py`

Fuehrt den autonomen Web-GUI-Qualitaetscheck aus:

- `py_compile` fuer die relevanten Python-Dateien
- `node --check` fuer `app/web/static/app.js`, falls `node` vorhanden ist
- `unittest`-Smokes fuer Web-Konsole und HTTP-Roundtrip

Optional:

- `python3 scripts/gui_quality_gate.py --debug-bundle-on-fail`

Dann wird bei einem Fehler direkt zusaetzlich ein Debug-Bundle erzeugt.

### `python3 scripts/collect_web_debug_bundle.py`

Erzeugt ein Debug-Paket unter `.web/debug-bundles/<timestamp>/` mit:

- `git status` und `git rev-parse HEAD`
- `py_compile`-Ergebnis
- HTML-, JS- und CSS-Snapshots
- API-Snapshots von:
  - `/`
  - `/api/status`
  - `/api/workbench`
  - `/api/browser-workflow`
  - `/api/processing/status`
- vorhandenem `swap_workbench.json`
- vorhandenem `runner.log`
- vorhandenem `status.json`
- DOM-ID-Vertragspruefung zwischen HTML und JS

## Tests

Die Datei `tests/test_web_console_smoke.py` prueft aktuell:

- HTML/JS-ID-Vertrag
- Vorhandensein der Kernbereiche in der Web-Konsole
- Stabilitaet der Workbench-Defaults
- isolierten Browser-Workflow mit temporaeren Upload-Verzeichnissen
- HTTP-Smoke fuer Root-Seite und Workbench-API

Wichtig:

- Diese Tests patchen die Modulpfade zur Laufzeit auf temporaere Verzeichnisse.
- Dadurch wird der echte Benutzerzustand nicht mit Testdaten verschmutzt.

## Autonomer Ablauf fuer mich

Wenn ich an der GUI arbeite, ist der neue Standardablauf:

1. Vor groesseren UI-Aenderungen `python3 scripts/gui_quality_gate.py`
2. Aenderungen implementieren
3. Danach erneut `python3 scripts/gui_quality_gate.py --debug-bundle-on-fail`
4. Bei Fehlern das erzeugte Bundle aus `.web/debug-bundles/` auswerten
5. Erst dann committen und pushen

## Naechster sinnvoller Ausbau

Die jetzige Basis ist absichtlich leichtgewichtig und ohne zusaetzliche Framework-Abhaengigkeiten gehalten.

Als naechste Stufe wuerde ich danach ergaenzen:

- Screenshot-basierte Browser-Smokes fuer Layout-Regressions
- gezielte Regressionstests fuer Job-Start und Direktlauf
- Fehlerklassen nach Bereichen:
  - DOM/Rendering
  - API/State
  - Headless-Runner
  - Upload/Workflow
- optional spaeter Playwright, falls wir die Browser-GUI wirklich pixelnah stabilisieren wollen
