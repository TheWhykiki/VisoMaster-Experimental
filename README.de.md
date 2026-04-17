# VisoMaster-Fusion mod

Diese Datei ist die deutsche Projektbeschreibung für die aktuell gepflegte Variante von VisoMaster-Fusion. Die englische [README.md](README.md) bleibt die technische Referenz, diese deutsche Fassung soll Installation, Start und Betriebsarten verständlicher machen.

## Überblick

VisoMaster-Fusion ist ein erweitertes Desktop-Werkzeug für Face-Swapping und Gesichtsverarbeitung in Bildern und Videos. Das Projekt kombiniert die ursprüngliche VisoMaster-Anwendung mit Erweiterungen aus der Community und bietet zusätzlich einen browserfähigen Web-Zugriff für Jobs, Presets und den Arbeitsbereichszustand.

Wichtige Punkte:

- Die **Desktop-GUI** bleibt die vollständige Hauptanwendung für die eigentliche Verarbeitung.
- Die **Web-Konsole** ist ein zusätzlicher Zugang über den Browser und ersetzt die Desktop-GUI nicht.
- Unter Windows erstellen die Startskripte bei Bedarf jetzt automatisch ein `visomaster`-Conda-Environment und installieren die Pakete aus `requirements_cu129.txt`.

## Hauptfunktionen

- Mehrere Face-Swap-Modelle
- Batch-Verarbeitung über eine Job-Verwaltung
- VR180-Unterstützung
- Erweiterte Restaurierung und Entrauschung
- Virtuelle Kamera für Live-Ausgabe
- Browserfähige Verwaltungsoberfläche für Jobs, Presets und `last_workspace.json`

## Voraussetzungen

Für die portable Variante brauchst du keine Vorinstallation.

Für die normale Variante sind hilfreich:

- `git`
- `Miniconda` oder `Anaconda`
- alternativ ein lokales `.venv`
- eine passende FFmpeg-Installation

Die aktuell gepflegte Abhängigkeitsdatei in diesem Repository ist:

```text
requirements_cu129.txt
```

## Betriebsarten

Dieses Repository unterstützt parallel zwei Modi:

1. **Originale Desktop-GUI**
   Die vollständige lokale `PySide6`-Anwendung für Face-Swap, Vorschau, Aufnahme und Bearbeitung.
2. **Web-Konsole**
   Eine zusätzliche Browser-Oberfläche für Status, Jobs, Presets und Arbeitsbereichsdaten.

## Schneller Start unter Windows

### Desktop-GUI

Starte einfach:

```text
Start.bat
```

Das Skript versucht in dieser Reihenfolge:

1. `.venv\Scripts\python.exe`
2. ein vorhandenes `visomaster`-Conda-Environment
3. ein gefundenes Conda mit automatischem Anlegen von `visomaster`
4. Windows-`py`
5. `python`

Wenn die benötigten Projektpakete fehlen, installiert das Skript automatisch `uv` und danach die Abhängigkeiten aus `requirements_cu129.txt`.

### Web-Konsole lokal

```text
Start_Web.bat
```

Danach ist die Oberfläche lokal erreichbar unter:

```text
http://127.0.0.1:8000
```

### Web-Konsole im Netzwerk

```text
Start_Web_Network.bat
```

Danach ist die Konsole über die im Terminal ausgegebene LAN-Adresse erreichbar. Unter Windows musst du Python gegebenenfalls in der Firewall freigeben.

## Portable Variante

Wenn du möglichst wenig manuell installieren willst, nutze:

```text
Start_Portable.bat
```

Zusätzliche portable Modi:

```text
Start_Portable.bat web
Start_Portable.bat web-network
```

Die portable Version lädt Python, `uv`, Git und weitere benötigte Komponenten beim ersten Start in den Ordner `portable-files`.

## Manuelle Installation ohne Starter

### Mit Conda

```sh
conda create -n visomaster python=3.11 -y
conda activate visomaster
pip install uv
uv pip install -r requirements_cu129.txt
python download_models.py
python main.py
```

### Mit `.venv`

```sh
uv venv --python 3.11
.venv\Scripts\activate
uv pip install -r requirements_cu129.txt
python download_models.py
python main.py
```

## Browser-Modus

Die Web-Konsole ist derzeit vor allem für Verwaltung und Einsicht gedacht. Sie kann bereits:

- Systemstatus anzeigen
- Jobs anzeigen, laden, speichern und löschen
- Job-Exporte anzeigen, laden, speichern und löschen
- Presets lesen, schreiben und löschen
- den letzten Arbeitsbereich lesen und speichern

Wichtig:

- Die eigentliche GPU-Verarbeitung läuft weiterhin primär über die Desktop-Architektur.
- Die Web-Konsole ist also aktuell eine sinnvolle Ergänzung, aber noch kein vollständiger Ersatz für die native Anwendung.

## Aktueller Architekturstand

Langfristig ist der sinnvolle Weg für Browser-Betrieb:

1. Verarbeitungslogik aus der Qt-Oberfläche lösen
2. daraus eine UI-unabhängige Service-Schicht machen
3. API-Endpunkte für Jobs, Uploads, Outputs und Steuerung aufbauen
4. die Web-Oberfläche als echten Client darauf aufsetzen

Genau deshalb existieren jetzt GUI und Web-Zugriff parallel nebeneinander.

## FFmpeg unter Windows

Entweder per `winget`:

```powershell
winget install -e --id Gyan.FFmpeg --version 7.1.1
```

Oder manuell:

- FFmpeg-ZIP herunterladen
- entpacken
- den `bin`-Ordner zur Windows-`PATH`-Variable hinzufügen

## Job-Verwaltung

Typischer Ablauf:

1. Medien und Gesichter laden
2. Parameter einstellen
3. Job speichern
4. mehrere Jobs sammeln
5. alle Jobs gesammelt verarbeiten

## Hinweis zur deutschen Übersetzung

Die Anwendung enthält jetzt eine erste sinnvolle deutsche Übersetzung für:

- die Hauptnavigation der Desktop-GUI
- zentrale Dialoge
- den erweiterten Embedding-Editor
- die Browser-Konsole
- API-Rückmeldungen der Web-Oberfläche

Einige technische Modellnamen und Fachbegriffe bleiben bewusst englisch, damit sie mit Dateinamen, Modellen und bestehenden Community-Anleitungen konsistent bleiben.
